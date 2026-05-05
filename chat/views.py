from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils.text import slugify
from .models import Room, Message, JoinRequest, Invitation
from django.db.models import OuterRef, Subquery
from datetime import timedelta
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

    # ── Public rooms with unread and online count ───────────────
    public_rooms_data = []
    for room in public_rooms:
        # Count online members in this room
        online_members = room.members.filter(is_online=True).count()
        public_rooms_data.append({
            'room': room,
            'unread': unread_for(room),
            'online_members': online_members,
        })

    # ── Private groups (member) with unread and online count ───────────────
    private_groups_data = []
    for room in my_private_groups:
        # Count online members in this room
        online_members = room.members.filter(is_online=True).count()
        private_groups_data.append({
            'room': room,
            'unread': unread_for(room),
            'online_members': online_members,
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
        # Count online members in this room
        online_members = room.members.filter(is_online=True).count()
        discoverable_groups_data.append({
            'room': room,
            'has_pending': room.id in user_pending_requests,
            'was_rejected': room.id in user_rejected_requests,
            'online_members': online_members,
        })

    # ── Pending join requests FOR rooms where user is admin (admin view) ──
    pending_approvals = JoinRequest.objects.filter(
        room__admin=request.user,
        room__is_private=True,
        status='pending',
    ).select_related('user', 'room').exclude(
        room__slug__startswith='dm-'
    )

    existing_dm_user_ids = [d['other_user'].id for d in dm_list]
    other_users = User.objects.exclude(id=request.user.id).exclude(id__in=existing_dm_user_ids)

    # All users for slideshow (exclude current user)
    all_users = User.objects.exclude(id=request.user.id)

    # ── Pending invitations for this user ──
    my_pending_invitations = Invitation.objects.filter(
        invited_user=request.user,
        status='pending',
    ).select_related('room', 'invited_by').exclude(
        room__slug__startswith='dm-'
    )

    return render(request, 'chat/index.html', {
        'rooms': public_rooms,
        'public_rooms_data': public_rooms_data,
        'private_groups_data': private_groups_data,
        'discoverable_groups_data': discoverable_groups_data,
        'dm_list': dm_list,
        'other_users': other_users,
        'all_users': all_users,
        'online_count': online_count,
        'messages_today': messages_today,
        'total_users': User.objects.count(),
        'pending_approvals': pending_approvals,
        'my_pending_invitations': my_pending_invitations,
    })


@login_required
def room(request, room_slug):
    
    last_message = Message.objects.filter(
    room=OuterRef('pk')).order_by('-timestamp')

    room = get_object_or_404(
    Room.objects.annotate(
        last_message_content=Subquery(last_message.values('content')[:1]),
        last_message_time=Subquery(last_message.values('timestamp')[:1]),
    ),slug=room_slug)

    if room.is_private and not room.members.filter(id=request.user.id).exists():
        raise Http404("Room not found")

    # Get last 50 messages (most recent)
    messages_qs = room.messages.select_related('author', 'reply_to__author').order_by('-timestamp')[:50][::-1]
    room.messages.exclude(author=request.user).filter(is_read=False).update(is_read=True)

    # Count online members in THIS room
    room_online_members = room.members.filter(
    last_seen__gte=timezone.now() - timedelta(minutes=1)
).count()

    public_rooms = Room.objects.filter(is_private=False).annotate(
    last_message_content=Subquery(last_message.values('content')[:1]),
    last_message_time=Subquery(last_message.values('timestamp')[:1]),
)
    my_private_rooms = Room.objects.filter(
    is_private=True,
    members=request.user
).annotate(
    last_message_content=Subquery(last_message.values('content')[:1]),
    last_message_time=Subquery(last_message.values('timestamp')[:1]),
)

    # Pending requests for this room (only admin can see)
    pending_requests = []
    # Users that can be invited (only admin can invite)
    inviteable_users = []
    is_admin = room.admin == request.user
    if room.is_private and is_admin:
        pending_requests = JoinRequest.objects.filter(
            room=room,
            status='pending',
        ).select_related('user')

        if not room.slug.startswith('dm-'):
            User = get_user_model()
            member_ids = room.members.values_list('id', flat=True)
            inviteable_users = User.objects.exclude(id__in=member_ids).exclude(id=request.user.id)

    return render(request, 'chat/room.html', {
        'room': room,
        'messages': messages_qs,
        'public_rooms': public_rooms,
        'my_private_rooms': my_private_rooms,
        'pending_requests': pending_requests,
        'inviteable_users': inviteable_users,
        'is_admin': is_admin,
        'room_online_members': room_online_members,
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
    Room admin approves or rejects a join request.
    action = 'approve' | 'reject'
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    jr = get_object_or_404(JoinRequest, id=request_id)

    # Only room admin can approve/reject
    if jr.room.admin != request.user:
        return JsonResponse({'error': 'Only room admin can approve/reject'}, status=403)

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
    """Returns HTML snippet of pending requests for rooms where user is admin (AJAX)."""
    pending = JoinRequest.objects.filter(
        room__admin=request.user,
        status='pending',
    ).select_related('user', 'room').exclude(room__slug__startswith='dm-')

    return render(request, 'chat/partials/pending_requests.html', {
        'pending_approvals': pending,
    })


# ── Private Room & Invitation Views ─────────────────────────────────────────

@login_required
def create_private_room(request):
    """Create a new private group room."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if not name:
        return JsonResponse({'error': 'Room name is required'}, status=400)

    if len(name) < 3:
        return JsonResponse({'error': 'Room name must be at least 3 characters'}, status=400)

    slug = slugify(name)
    if not slug:
        return JsonResponse({'error': 'Invalid room name'}, status=400)

    # Ensure unique slug
    base_slug = slug
    counter = 1
    while Room.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    # Ensure unique name
    base_name = name
    counter = 1
    while Room.objects.filter(name=name).exists():
        name = f'{base_name} ({counter})'
        counter += 1

    room = Room.objects.create(
        name=name,
        slug=slug,
        description=description,
        is_private=True,
        admin=request.user,
    )
    room.members.add(request.user)

    return JsonResponse({
        'ok': True,
        'room_slug': room.slug,
        'room_name': room.name,
        'message': f'Private room "{room.name}" created!',
    })


@login_required
def invite_to_room(request, room_slug):
    """Invite a user to a private room."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug, is_private=True)

    # Only admin can invite
    if room.admin != request.user:
        return JsonResponse({'error': 'Only room admin can invite'}, status=403)

    # DM rooms cannot be invited to
    if room.slug.startswith('dm-'):
        return JsonResponse({'error': 'Cannot invite to a DM room'}, status=400)

    username = request.POST.get('username', '').strip()
    if not username:
        return JsonResponse({'error': 'Username is required'}, status=400)

    User = get_user_model()
    try:
        invited_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': f'User "{username}" not found'}, status=404)

    if invited_user == request.user:
        return JsonResponse({'error': 'Cannot invite yourself'}, status=400)

    # Already a member?
    if room.members.filter(id=invited_user.id).exists():
        return JsonResponse({'error': f'{username} is already a member'}, status=400)

    # Already invited?
    inv, created = Invitation.objects.get_or_create(
        room=room,
        invited_user=invited_user,
        defaults={
            'invited_by': request.user,
            'status': 'pending',
        },
    )

    if not created:
        if inv.status == 'accepted':
            return JsonResponse({'error': f'{username} already accepted the invitation'}, status=400)
        if inv.status == 'declined':
            # Re-invite
            inv.invited_by = request.user
            inv.status = 'pending'
            inv.save(update_fields=['invited_by', 'status', 'updated_at'])
            return JsonResponse({'ok': True, 'message': f'Re-invitation sent to {username}!'})
        return JsonResponse({'ok': True, 'message': f'{username} already has a pending invitation'})

    return JsonResponse({'ok': True, 'message': f'Invitation sent to {username}!'})


@login_required
def handle_invitation(request, invitation_id, action):
    """Accept or decline an invitation."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    inv = get_object_or_404(Invitation, id=invitation_id, invited_user=request.user)

    if inv.status != 'pending':
        return JsonResponse({'error': 'Invitation already handled'}, status=400)

    if action == 'accept':
        inv.status = 'accepted'
        inv.save(update_fields=['status', 'updated_at'])
        inv.room.members.add(inv.invited_user)
        return JsonResponse({
            'ok': True,
            'action': 'accepted',
            'room_slug': inv.room.slug,
            'room_name': inv.room.name,
        })
    elif action == 'decline':
        inv.status = 'declined'
        inv.save(update_fields=['status', 'updated_at'])
        return JsonResponse({'ok': True, 'action': 'declined'})
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)


@login_required
def my_invitations(request):
    """Returns HTML snippet of pending invitations for the current user (AJAX)."""
    invitations = Invitation.objects.filter(
        invited_user=request.user,
        status='pending',
    ).select_related('room', 'invited_by').exclude(
        room__slug__startswith='dm-'
    )

    return render(request, 'chat/partials/my_invitations.html', {
        'invitations': invitations,
    })


# ── Room Settings ─────────────────────────────────────────────────────────

@login_required
def remove_member(request, room_slug):
    """Room admin removes a member from the room."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug, is_private=True)

    # Only admin can remove members
    if room.admin != request.user:
        return JsonResponse({'error': 'Only room admin can remove members'}, status=403)

    username = request.POST.get('username', '').strip()
    if not username:
        return JsonResponse({'error': 'Username is required'}, status=400)

    User = get_user_model()
    try:
        member = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': f'User "{username}" not found'}, status=404)

    # Cannot remove admin (self)
    if member == room.admin:
        return JsonResponse({'error': 'Cannot remove the room admin'}, status=400)

    # Check if user is a member
    if not room.members.filter(id=member.id).exists():
        return JsonResponse({'error': f'{username} is not a member of this room'}, status=400)

    room.members.remove(member)
    return JsonResponse({'ok': True, 'message': f'{username} has been removed from the room'})


@login_required
def room_settings(request, room_slug):
    """Room settings page — edit name/description or delete room (admin only)."""
    room = get_object_or_404(Room, slug=room_slug, is_private=True)

    # Only admin can access settings
    if room.admin != request.user:
        raise Http404("Access denied")

    # DM rooms have no settings
    if room.slug.startswith('dm-'):
        raise Http404("DM rooms have no settings")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'edit':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()

            if not name or len(name) < 3:
                messages.error(request, 'Room name must be at least 3 characters.')
                return redirect('chat:room_settings', room_slug=room_slug)

            # Check unique name (excluding this room)
            if Room.objects.filter(name=name).exclude(slug=room_slug).exists():
                messages.error(request, f'Room name "{name}" is already taken.')
                return redirect('chat:room_settings', room_slug=room_slug)

            room.name = name
            room.description = description
            room.save(update_fields=['name', 'description', 'updated_at'])
            messages.success(request, 'Room updated successfully!')
            return redirect('chat:room_settings', room_slug=room_slug)

        elif action == 'change_avatar':
            avatar = request.FILES.get('avatar')
            if avatar:
                # Delete old avatar if exists
                if room.avatar:
                    room.avatar.delete(save=False)
                room.avatar = avatar
                room.save(update_fields=['avatar', 'updated_at'])
                messages.success(request, 'Room avatar updated successfully!')
            else:
                messages.error(request, 'Please select an image to upload.')
            return redirect('chat:room_settings', room_slug=room_slug)

        elif action == 'delete':
            room.delete()
            messages.success(request, f'Room deleted.')
            return redirect('chat:index')

    # Stats
    total_messages = room.messages.count()
    pending_count = JoinRequest.objects.filter(room=room, status='pending').count()
    member_count = room.members.count()

    return render(request, 'chat/room_settings.html', {
        'room': room,
        'total_messages': total_messages,
        'pending_count': pending_count,
        'member_count': member_count,
    })


@login_required
def load_older_messages(request, room_slug):
    """API endpoint to load older messages (pagination)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'GET only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug)

    if room.is_private and not room.members.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Get the oldest message ID currently loaded
    before_id = request.GET.get('before_id')
    if not before_id:
        return JsonResponse({'error': 'before_id is required'}, status=400)

    try:
        before_id = int(before_id)
    except ValueError:
        return JsonResponse({'error': 'Invalid before_id'}, status=400)

    # Get the timestamp of the reference message
    try:
        ref_message = Message.objects.get(id=before_id, room=room)
    except Message.DoesNotExist:
        return JsonResponse({'error': 'Message not found'}, status=404)

    # Get 50 messages older than the reference message
    messages_qs = room.messages.filter(
        timestamp__lt=ref_message.timestamp
    ).select_related('author', 'reply_to__author').order_by('-timestamp')[:50]

    messages_data = []
    for msg in messages_qs[::-1]:  # Reverse to get chronological order
        msg_data = {
            'id': msg.id,
            'content': msg.content,
            'author': msg.author.username,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'is_edited': msg.is_edited,
            'is_read': msg.is_read,
            'is_own': msg.author == request.user,
            'file_url': msg.file.url if msg.file else None,
            'file_type': msg.file_type,
        }
        if msg.reply_to:
            msg_data['reply_to'] = {
                'id': msg.reply_to.id,
                'username': msg.reply_to.author.username,
                'text': msg.reply_to.content[:80] if not msg.reply_to.file else f'📎 {msg.reply_to.content}',
            }
        messages_data.append(msg_data)

    return JsonResponse({
        'messages': messages_data,
        'has_more': room.messages.filter(timestamp__lt=ref_message.timestamp).count() > 50,
    })