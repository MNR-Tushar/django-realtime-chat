from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Room, Message


@login_required
def index(request):
    """Chat room list page"""
    rooms = Room.objects.all()
    return render(request, 'chat/index.html', {'rooms': rooms})


@login_required
def room(request, room_slug):
    """Chat room page"""
    room = get_object_or_404(Room, slug=room_slug)
    
    
    messages = room.messages.select_related('author')[:50]
    return render(request, 'chat/room.html', {
        'room': room,
        'messages': messages,
    })