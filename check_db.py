import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatproject.settings')
django.setup()

from chat.models import Room, Message
from django.contrib.auth import get_user_model

User = get_user_model()

print(f"Total Rooms: {Room.objects.count()}")
print(f"Total Messages: {Message.objects.count()}")
print(f"Total Users: {User.objects.count()}")

# List all rooms
for room in Room.objects.all():
    print(f"  - {room.name} ({room.slug})")

# Create a test room if none exist
if Room.objects.count() == 0:
    room = Room.objects.create(name="General", slug="general", description="General chat room")
    print(f"Created new room: {room.name}")
    
print("\nSetup complete!")
