import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.me = self.scope['user']
        self.other_username = self.scope['url_route']['kwargs']['username']

        # Create a consistent room name regardless of who connects first
        names = sorted([self.me.username, self.other_username])
        self.room_group_name = f"chat_{'_'.join(names)}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # Join global presence group
        await self.channel_layer.group_add('global_presence', self.channel_name)
        
        await self.accept()

        # Mark messages from the other user as read
        await self.mark_messages_read()
        
        # Set online status and broadcast
        await self.set_online_status(True)
        await self.channel_layer.group_send(
            'global_presence',
            {
                'type': 'user_status',
                'username': self.me.username,
                'is_online': True
            }
        )

    async def disconnect(self, close_code):
        # Set offline status and broadcast
        await self.set_online_status(False)
        await self.channel_layer.group_send(
            'global_presence',
            {
                'type': 'user_status',
                'username': self.me.username,
                'is_online': False
            }
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_discard('global_presence', self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', 'send')
        
        if action == 'send':
            content = data.get('message', '').strip()
            if not content: return
            
            message = await self.save_message(content)
            profile_pic_url = await self.get_profile_pic_url()
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'id': message.id,
                    'message': content,
                    'sender': self.me.username,
                    'timestamp': message.timestamp.strftime('%H:%M'),
                    'profile_pic': profile_pic_url,
                }
            )
            
        elif action == 'edit':
            message_id = data.get('message_id')
            new_content = data.get('content', '').strip()
            if not message_id or not new_content: return
            
            success = await self.edit_message(message_id, new_content)
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_edited',
                        'id': message_id,
                        'content': new_content,
                    }
                )
                
        elif action == 'delete':
            message_id = data.get('message_id')
            if not message_id: return
            
            success = await self.delete_message(message_id)
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_deleted',
                        'id': message_id,
                    }
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'id': event.get('id'),
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp'],
            'profile_pic': event.get('profile_pic', ''),
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'id': event['id'],
            'content': event['content'],
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'id': event['id'],
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'username': event['username'],
            'is_online': event['is_online'],
        }))

    # ── DB helpers (run in thread pool) ────────────────────────────────────────

    @database_sync_to_async
    def set_online_status(self, is_online):
        if hasattr(self.me, 'profile'):
            self.me.profile.is_online = is_online
            self.me.profile.save(update_fields=['is_online'])

    @database_sync_to_async
    def save_message(self, content):
        other_user = User.objects.get(username=self.other_username)
        return Message.objects.create(
            sender=self.me,
            receiver=other_user,
            content=content,
        )

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        try:
            # Verify ownership before editing
            msg = Message.objects.get(id=message_id, sender=self.me)
            msg.content = new_content
            msg.save(update_fields=['content'])
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def delete_message(self, message_id):
        try:
            # Verify ownership before deleting
            msg = Message.objects.get(id=message_id, sender=self.me)
            msg.delete()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_messages_read(self):
        other_user = User.objects.filter(username=self.other_username).first()
        if other_user:
            Message.objects.filter(
                sender=other_user,
                receiver=self.me,
                read=False
            ).update(read=True)

    @database_sync_to_async
    def get_profile_pic_url(self):
        try:
            profile = self.me.profile
            if profile.profile_picture:
                return profile.profile_picture.url
        except Exception:
            pass
        return ''