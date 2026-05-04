import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Room


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'chat_{self.room_slug}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        is_allowed = await self.check_room_access()
        if not is_allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.set_user_online(True)

        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_join', 'username': self.user.username}
        )

        count = await self.get_online_count()
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'online_count', 'count': count}
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.set_user_online(False)
            count = await self.get_online_count()
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'online_count', 'count': count}
                )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')

        if event_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_typing', 'username': self.user.username}
            )
            return

        if event_type == 'stop_typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_stop_typing', 'username': self.user.username}
            )
            return

        if event_type == 'mark_as_read':
            message_id = data.get('message_id')
            await self.mark_message_as_read(message_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'username': self.user.username,
                }
            )
            return

        if event_type == 'file_message':
            file_url   = data.get('file_url', '')
            file_type  = data.get('file_type', 'file')
            file_name  = data.get('file_name', 'file')
            message_id = data.get('message_id')
            timestamp  = await self.get_message_timestamp(message_id)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':       'chat_message',
                    'message':    file_name,
                    'username':   self.user.username,
                    'timestamp':  timestamp,
                    'message_id': message_id,
                    'file_url':   file_url,
                    'file_type':  file_type,
                }
            )
            return

        # ── Delete message ──────────────────────────────
        if event_type == 'delete_message':
            message_id = data.get('message_id')
            deleted = await self.delete_message(message_id)
            if deleted:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type':       'message_deleted',
                        'message_id': message_id,
                    }
                )
            return

        # ── Edit message ────────────────────────────────
        if event_type == 'edit_message':
            message_id = data.get('message_id')
            new_content = data.get('content', '').strip()
            if not new_content:
                return
            edited = await self.edit_message(message_id, new_content)
            if edited:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type':       'message_edited',
                        'message_id': message_id,
                        'content':    new_content,
                    }
                )
            return

        # Regular text message
        message_content = data.get('message', '').strip()
        if not message_content:
            return

        message = await self.save_message(message_content)
        if message is None:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':       'chat_message',
                'message':    message_content,
                'username':   self.user.username,
                'timestamp':  message.timestamp.strftime('%H:%M'),
                'message_id': message.id,
                'file_url':   None,
                'file_type':  None,
            }
        )

    # ── Handlers ──────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type':       'chat_message',
            'message':    event['message'],
            'username':   event['username'],
            'timestamp':  event['timestamp'],
            'message_id': event['message_id'],
            'file_url':   event.get('file_url'),
            'file_type':  event.get('file_type'),
        }))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing', 'username': event['username']
        }))

    async def user_stop_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'stop_typing', 'username': event['username']
        }))

    async def user_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_join', 'username': event['username']
        }))

    async def online_count(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_count', 'count': event['count']
        }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type':       'message_read',
            'message_id': event['message_id'],
            'username':   event['username'],
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type':       'message_deleted',
            'message_id': event['message_id'],
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type':       'message_edited',
            'message_id': event['message_id'],
            'content':    event['content'],
        }))

    # ── DB Helpers ────────────────────────────

    @database_sync_to_async
    def check_room_access(self):
        try:
            room = Room.objects.get(slug=self.room_slug)
            if room.is_private:
                return room.members.filter(id=self.user.id).exists()
            return True
        except Room.DoesNotExist:
            return False

    @database_sync_to_async
    def get_online_count(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.filter(is_online=True).count()

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            msg.is_read = True
            msg.save(update_fields=['is_read'])
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def save_message(self, content):
        try:
            room = Room.objects.get(slug=self.room_slug)
            return Message.objects.create(room=room, author=self.user, content=content)
        except Room.DoesNotExist:
            return None

    @database_sync_to_async
    def get_message_timestamp(self, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            return msg.timestamp.strftime('%H:%M')
        except Message.DoesNotExist:
            from django.utils import timezone
            return timezone.now().strftime('%H:%M')

    @database_sync_to_async
    def set_user_online(self, status):
        self.user.is_online = status
        self.user.save(update_fields=['is_online'])

    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete a message only if the current user is the author."""
        try:
            msg = Message.objects.get(id=message_id, author=self.user)
            msg.delete()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit a message only if the current user is the author."""
        try:
            msg = Message.objects.get(id=message_id, author=self.user)
            msg.content = new_content
            msg.is_edited = True
            msg.save(update_fields=['content', 'is_edited'])
            return True
        except Message.DoesNotExist:
            return False