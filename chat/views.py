from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Room, Message


@login_required
def index(request):
    """Chat room list page"""
    User = get_user_model()
    rooms = Room.objects.all()
    online_count = User.objects.filter(is_online=True).count()
    messages_today = Message.objects.filter(timestamp__date=timezone.now().date()).count()
    total_users = User.objects.count()
    all_users = User.objects.all()

    return render(request, 'chat/index.html', {
        'rooms': rooms,
        'online_count': online_count,
        'messages_today': messages_today,
        'total_users': total_users,
        'all_users': all_users,
    })


@login_required
def room(request, room_slug):
    """Chat room page"""
    room = get_object_or_404(Room, slug=room_slug)
    messages = room.messages.select_related('author')[:50]
    room.messages.exclude(author=request.user).filter(is_read=False).update(is_read=True)
    return render(request, 'chat/room.html', {
        'room': room,
        'messages': messages,
    })


@login_required
def direct_message(request, username):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other_user = get_object_or_404(User, username=username)
    room = Room.get_or_create_private(request.user, other_user)
    return redirect('chat:room', room_slug=room.slug)



@login_required
def upload_file(request, room_slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(Room, slug=room_slug)
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
    return JsonResponse({'url': msg.file.url, 'id': msg.id})