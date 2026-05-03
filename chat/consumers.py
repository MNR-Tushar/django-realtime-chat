import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message, Room


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        """Client WebSocket connect"""
        #
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'chat_{self.room_slug}'
        self.user = self.scope['user']

        # Authenticated user check 
        if not self.user.is_authenticated:
            await self.close()
            return

        # Channel Group join
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        # Connection accept
        await self.accept()

        # User online mark 
        await self.set_user_online(True)

        # User join notification
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'username': self.user.username,
            }
        )

    async def disconnect(self, close_code):
        """Client disconnect"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.set_user_online(False)

    async def receive(self, text_data):
        """Client message"""
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()

        if not message_content:
            return

        # Message save
        message = await self.save_message(message_content)

        # Message send to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'username': self.user.username,
                'timestamp': message.timestamp.strftime('%H:%M'),
                'message_id': message.id,
            }
        )

    async def chat_message(self, event):
        """Message send to client"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
        }))

    async def user_join(self, event):
        """User join notification"""
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'username': event['username'],
        }))

    # ── Database helpers (sync → async) ──

    @database_sync_to_async
    def save_message(self, content):
        room = Room.objects.get(slug=self.room_slug)
        return Message.objects.create(
            room=room,
            author=self.user,
            content=content
        )

    @database_sync_to_async
    def set_user_online(self, status):
        self.user.is_online = status
        self.user.save(update_fields=['is_online'])