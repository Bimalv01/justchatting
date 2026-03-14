import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.me = self.scope['user']
        if not self.me.is_authenticated:
            await self.close()
            return

        self.other_username = self.scope['url_route']['kwargs']['username']

        # Create a consistent room name regardless of who connects first
        names = sorted([self.me.username, self.other_username])
        self.room_group_name = f"chat_{'_'.join(names)}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # Join global presence group
        await self.channel_layer.group_add('global_presence', self.channel_name)
        # Join personal notification group
        await self.channel_layer.group_add(f"user_{self.me.username}", self.channel_name)
        
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
        await self.channel_layer.group_discard(f"user_{self.me.username}", self.channel_name)

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
            
            # Also notify the recipient's personal group for sidebar/unread
            await self.channel_layer.group_send(
                f"user_{self.other_username}",
                {
                    'type': 'user_notification',
                    'id': message.id,
                    'sender': self.me.username,
                    'message': content,
                    'timestamp': message.timestamp.strftime('%H:%M'),
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
                
        elif action == 'read_receipt':
            # Sender of this action is the recipient of the messages
            unread_count = await self.mark_messages_read()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'reader': self.me.username,
                }
            )
            # Notify self to update sidebar if needed
            await self.send(text_data=json.dumps({
                'type': 'unread_count_update',
                'username': self.other_username,
                'count': unread_count
            }))

    async def chat_message(self, event):
        sender_name = event['sender']
        message_id = event.get('id')
        
        # If I am the recipient, mark as delivered and notify sender
        if sender_name != self.me.username:
            await self.set_message_delivered(message_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_delivered',
                    'id': message_id,
                    'is_delivered': True,
                    'sender': sender_name # who sent it
                }
            )
            # Acknowledge receipt back to the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_delivered',
                    'id': message_id,
                    'is_delivered': True,
                    'sender': sender_name
                }
            )

        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'id': message_id,
            'message': event['message'],
            'sender': sender_name,
            'timestamp': event['timestamp'],
            'profile_pic': event.get('profile_pic', ''),
            'is_read': False,
            'is_delivered': sender_name != self.me.username # it's delivered if we are here
        }))

    async def user_notification(self, event):
        sender_name = event['sender']
        message_id = event['id']
        
        # If I am the recipient, mark as delivered and notify sender
        if sender_name != self.me.username:
            await self.set_message_delivered(message_id)
            
            # Construction of the room name for that specific chat-room to notify original sender
            names = sorted([self.me.username, sender_name])
            specific_room = f"chat_{'_'.join(names)}"
            
            await self.channel_layer.group_send(
                specific_room,
                {
                    'type': 'message_delivered',
                    'id': message_id,
                    'is_delivered': True,
                    'sender': sender_name
                }
            )
            
            # Fetch unread count to update sidebar in real-time
            unread_count = await self.get_unread_count(sender_name)
            await self.send(text_data=json.dumps({
                'type': 'unread_count_update',
                'username': sender_name,
                'count': unread_count,
                'message': event['message'],
                'timestamp': event['timestamp']
            }))

    async def message_delivered(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_status_update',
            'id': event['id'],
            'status': 'delivered'
        }))

    async def messages_read(self, event):
        # Notify the original sender that their messages were read
        if event['reader'] != self.me.username:
            await self.send(text_data=json.dumps({
                'type': 'message_status_update',
                'status': 'read'
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
            msg.is_deleted = True
            msg.save(update_fields=['is_deleted'])
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
            return Message.objects.filter(sender=other_user, receiver=self.me, read=False).count()
        return 0

    @database_sync_to_async
    def set_message_delivered(self, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            msg.is_delivered = True
            msg.save(update_fields=['is_delivered'])
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def get_unread_count(self, sender_username):
        try:
            sender = User.objects.get(username=sender_username)
            return Message.objects.filter(sender=sender, receiver=self.me, read=False).count()
        except User.DoesNotExist:
            return 0

    @database_sync_to_async
    def get_profile_pic_url(self):
        try:
            profile = self.me.profile
            if profile.profile_picture:
                return profile.profile_picture.url
        except Exception:
            pass
        return ''