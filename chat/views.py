from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Room, Message


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

    online_count = User.objects.filter(is_online=True).count()
    messages_today = Message.objects.filter(timestamp__date=timezone.now().date()).count()

    
    dm_list = []
    for dm_room in my_dm_rooms:
        other = dm_room.members.exclude(id=request.user.id).first()
        if other:
            dm_list.append({'room': dm_room, 'other_user': other})

    
    existing_dm_user_ids = [d['other_user'].id for d in dm_list]
    other_users = User.objects.exclude(id=request.user.id).exclude(id__in=existing_dm_user_ids)

    return render(request, 'chat/index.html', {
        'rooms': public_rooms,
        'my_private_groups': my_private_groups,  
        'dm_list': dm_list,
        'other_users': other_users,
        'online_count': online_count,
        'messages_today': messages_today,
        'total_users': User.objects.count(),
    })


@login_required
def room(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)

    if room.is_private and not room.members.filter(id=request.user.id).exists():
        raise Http404("Room not found")

    messages = room.messages.select_related('author')[:50]
    room.messages.exclude(author=request.user).filter(is_read=False).update(is_read=True)

    
    public_rooms = Room.objects.filter(is_private=False)
    my_private_rooms = Room.objects.filter(is_private=True, members=request.user)

    return render(request, 'chat/room.html', {
        'room': room,
        'messages': messages,
        'public_rooms': public_rooms,
        'my_private_rooms': my_private_rooms,
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