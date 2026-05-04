from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from .models import Room, Message, JoinRequest


@login_required
def index(request):
    User = get_user_model()

    # public rooms — is_private=False
    public_rooms = Room.objects.filter(is_private=False)

    my_private_groups = Room.objects.filter(
        is_private=True,
        members=request.user
    ).exclude(slug__startswith='dm-')

    my_dm_rooms = Room.objects.filter(
        is_private=True,
        members=request.user,
        slug__startswith='dm-'
    )

    # All private groups that user is NOT a member of (excludes DM rooms)
    all_private_groups = Room.objects.filter(
        is_private=True,
    ).exclude(
        slug__startswith='dm-'
    ).exclude(
        members=request.user
    )

    online_count = User.objects.filter(is_online=True).count()
    messages_today = Message.objects.filter(timestamp__date=timezone.now().date()).count()

    # ── Unread counts helper ───────────────────
    def unread_for(room):
        return Message.objects.filter(
            room=room,
            is_read=False,
        ).exclude(author=request.user).count()

    # ── DM list with unread ────────────────────
    dm_list = []
    for dm_room in my_dm_rooms:
        other = dm_room.members.exclude(id=request.user.id).first()
        if other:
            dm_list.append({
                'room': dm_room,
                'other_user': other,
                'unread': unread_for(dm_room),
            })

    # ── Public rooms with unread ───────────────
    public_rooms_data = []
    for room in public_rooms:
        public_rooms_data.append({
            'room': room,
            'unread': unread_for(room),
        })

    # ── Private groups (member) with unread ───────────────
    private_groups_data = []
    for room in my_private_groups:
        private_groups_data.append({
            'room': room,
            'unread': unread_for(room),
        })

    # ── Discoverable private groups (non-member) ───────────
    discoverable_groups_data = []
    # Fetch all pending requests by this user in one query
    user_pending_requests = set(
        JoinRequest.objects.filter(
            user=request.user,
            status='pending',
        ).values_list('room_id', flat=True)
    )
    user_rejected_requests = set(
        JoinRequest.objects.filter(
            user=request.user,
            status='rejected',
        ).values_list('room_id', flat=True)
    )
    for room in all_private_groups:
        discoverable_groups_data.append({
            'room': room,
            'has_pending': room.id in user_pending_requests,
            'was_rejected': room.id in user_rejected_requests,
        })

    # ── Pending join requests FOR rooms where user is a member (admin view) ──
    pending_approvals = JoinRequest.objects.filter(
        room__members=request.user,
        room__is_private=True,
        status='pending',
    ).select_related('user', 'room').exclude(
        room__slug__startswith='dm-'
    )

    existing_dm_user_ids = [d['other_user'].id for d in dm_list]
    other_users = User.objects.exclude(id=request.user.id).exclude(id__in=existing_dm_user_ids)

    return render(request, 'chat/index.html', {
        'rooms': public_rooms,
        'public_rooms_data': public_rooms_data,
        'private_groups_data': private_groups_data,
        'discoverable_groups_data': discoverable_groups_data,
        'dm_list': dm_list,
        'other_users': other_users,
        'online_count': online_count,
        'messages_today': messages_today,
        'total_users': User.objects.count(),
        'pending_approvals': pending_approvals,
    })


@login_required
def room(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)

    if room.is_private and not room.members.filter(id=request.user.id).exists():
        raise Http404("Room not found")

    messages_qs = room.messages.select_related('author', 'reply_to__author')[:50]
    room.messages.exclude(author=request.user).filter(is_read=False).update(is_read=True)

    public_rooms = Room.objects.filter(is_private=False)
    my_private_rooms = Room.objects.filter(is_private=True, members=request.user)

    # Pending requests for this room (for member/admin to see)
    pending_requests = []
    if room.is_private and room.members.filter(id=request.user.id).exists():
        pending_requests = JoinRequest.objects.filter(
            room=room,
            status='pending',
        ).select_related('user')

    return render(request, 'chat/room.html', {
        'room': room,
        'messages': messages_qs,
        'public_rooms': public_rooms,
        'my_private_rooms': my_private_rooms,
        'pending_requests': pending_requests,
    })


@login_required
def direct_message(request, username):
    User = get_user_model()
    if username == request.user.username:
        return redirect('chat:index')
    other_user = get_object_or_404(User, username=username)
    room = Room.get_or_create_private(request.user, other_user)
    return redirect('chat:room', room_slug=room.slug)


@login_required
def upload_file(request, room_slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug)

    if room.is_private and not room.members.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)

    uploaded = request.FILES.get('file')
    if not uploaded:
        return JsonResponse({'error': 'No file'}, status=400)

    msg = Message.objects.create(
        room=room,
        author=request.user,
        content=uploaded.name,
        file=uploaded,
        file_type='image' if uploaded.content_type.startswith('image') else 'file'
    )
    return JsonResponse({'url': msg.file.url, 'id': msg.id, 'file_type': msg.file_type})


# ── Join Request Views ─────────────────────────────────────────────────────

@login_required
def request_join(request, room_slug):
    """User sends a join request for a private room."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug, is_private=True)

    # DM rooms cannot be joined this way
    if room.slug.startswith('dm-'):
        return JsonResponse({'error': 'Cannot request to join a DM room'}, status=400)

    # Already a member?
    if room.members.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'Already a member'}, status=400)

    jr, created = JoinRequest.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={'status': 'pending'},
    )

    if not created:
        if jr.status == 'approved':
            return JsonResponse({'error': 'Already approved'}, status=400)
        # Reset rejected to pending so user can re-request
        if jr.status == 'rejected':
            jr.status = 'pending'
            jr.save(update_fields=['status', 'updated_at'])
            return JsonResponse({'ok': True, 'status': 'pending', 'message': 'Request re-sent!'})
        return JsonResponse({'ok': True, 'status': 'pending', 'message': 'Already requested'})

    return JsonResponse({'ok': True, 'status': 'pending', 'message': 'Request sent!'})


@login_required
def cancel_join_request(request, room_slug):
    """User cancels their own pending join request."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug)
    jr = get_object_or_404(JoinRequest, room=room, user=request.user, status='pending')
    jr.delete()
    return JsonResponse({'ok': True, 'message': 'Request cancelled'})


@login_required
def handle_join_request(request, request_id, action):
    """
    Room member approves or rejects a join request.
    action = 'approve' | 'reject'
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    jr = get_object_or_404(JoinRequest, id=request_id)

    # Only existing room members can approve/reject
    if not jr.room.members.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if action == 'approve':
        jr.status = 'approved'
        jr.save(update_fields=['status', 'updated_at'])
        jr.room.members.add(jr.user)
        return JsonResponse({'ok': True, 'action': 'approved', 'username': jr.user.username})
    elif action == 'reject':
        jr.status = 'rejected'
        jr.save(update_fields=['status', 'updated_at'])
        return JsonResponse({'ok': True, 'action': 'rejected', 'username': jr.user.username})
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)


@login_required
def pending_requests_panel(request):
    """Returns HTML snippet of pending requests for rooms where user is a member (AJAX)."""
    pending = JoinRequest.objects.filter(
        room__members=request.user,
        status='pending',
    ).select_related('user', 'room').exclude(room__slug__startswith='dm-')

    return render(request, 'chat/partials/pending_requests.html', {
        'pending_approvals': pending,
    })