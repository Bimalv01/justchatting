# chat/views.py

import os
import uuid
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .models import Message, Profile
from django.contrib import messages
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import cmake
import base64


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. You are now logged in.")
            return redirect('chat_room')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm


def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'profile.html', {'form': form})

import face_recognition
from django.core.files.storage import default_storage

def facial_login(request):
    if request.method == 'POST':
        image_data = request.POST.get('file')
        if image_data:
            format, imgstr = image_data.split(';base64,') 
            ext = format.split('/')[-1] 
            file_name = f"facial_login_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = os.path.join(settings.MEDIA_ROOT, 'temp', file_name)

            # Decode the image and save it
            with default_storage.open(file_path, 'wb+') as destination:
                destination.write(base64.b64decode(imgstr))

            try:
                image = face_recognition.load_image_file(file_path)
                face_encodings = face_recognition.face_encodings(image)
                if face_encodings:
                    user = None
                    for u in User.objects.all():
                        if u.profile.profile_picture:
                            user_image = face_recognition.load_image_file(u.profile.profile_picture.path)
                            user_face_encoding = face_recognition.face_encodings(user_image)[0]
                            if face_recognition.compare_faces([user_face_encoding], face_encodings[0])[0]:
                                user = u
                                break

                    if user:
                        login(request, user)
                        return redirect('chat_room')
                    else:
                        return HttpResponse("Facial recognition failed", status=401)
                else:
                    return HttpResponse("No face detected", status=400)
            except FileNotFoundError as e:
                return HttpResponse(f"File not found: {e}", status=404)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        else:
            return HttpResponse("No image data", status=400)
    else:
        return render(request, 'facial_login.html')
    
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login successful.")
            return redirect('chat_room')
        else:
            messages.error(request, "Login failed. Please check your credentials and try again.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

from django.contrib.auth.models import User
from django.db.models import Max
from django.db.models import Q

@login_required
def chat_room(request):
    logged_in_user = request.user
    other_users = User.objects.exclude(pk=logged_in_user.pk).exclude(is_superuser=True)

    search_query = request.GET.get('search')

    if search_query:
        other_users = other_users.filter(username__icontains=search_query)

    # Fetch recent messages sent to or received from each user
    for user in other_users:
        recent_message = Message.objects.filter(
            Q(sender=logged_in_user, receiver=user) | Q(sender=user, receiver=logged_in_user)
        ).order_by('-timestamp').first()

        user.recent_message = recent_message  # Add recent message to user object

        # Calculate unread message count for the user
    for user in other_users:
        recent_unread_message = Message.objects.filter(
            sender=user, receiver=logged_in_user, read=False
        ).order_by('-timestamp').first()

        user.recent_unread_message = recent_unread_message  # Add recent unread message to user object

    return render(request, 'chat_room.html', {'other_users': other_users})


from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from .models import Message
from django.http import Http404, HttpResponse
@login_required
def start_chat(request, username):
    try:
        # Retrieve the other user object based on the username
        other_user = get_object_or_404(User, username=username)
        
        # Retrieve the logged-in user
        logged_in_user = request.user
        
        # Retrieve the chat history between the logged-in user and the other user
        chat_history = Message.objects.filter(sender=logged_in_user, receiver=other_user) | \
                       Message.objects.filter(sender=other_user, receiver=logged_in_user)

        # Order the chat history by timestamp
        chat_history = chat_history.order_by('timestamp')

        # Retrieve other users excluding the logged-in user and admin users
        other_users = User.objects.exclude(pk=logged_in_user.pk).exclude(is_superuser=True)

        return render(request, 'start_chat.html', {
            'other_user': other_user,
            'chat_history': chat_history,
            'other_users': other_users
        })
    except User.DoesNotExist:
        raise Http404("User does not exist")
@login_required   
def send_message(request, username):
    if request.method == "POST":
        other_user = get_object_or_404(User, username=username)
        logged_in_user = request.user
        message_content = request.POST.get('message_content')

        if message_content:
            Message.objects.create(
                sender=logged_in_user,
                receiver=other_user,
                content=message_content
            )

        return redirect('start_chat', username=username)
    
def edit_message(request, message_id):
    message = get_object_or_404(Message, pk=message_id)

    if request.method == 'POST':
        new_content = request.POST.get('message_content')
        if new_content:
            message.content = new_content
            message.save()
            return redirect('start_chat', username=message.receiver.username)

    return redirect('start_chat', username=message.receiver.username)

def delete_message(request, message_id):
    message = get_object_or_404(Message, pk=message_id)
    receiver_username = message.receiver.username
    message.delete()
    return redirect('start_chat', username=receiver_username)

from django.http import JsonResponse
from .models import Message

def get_chat_messages(request):
    messages = Message.objects.all()  # Fetch all messages from the database
    data = [{'content': message.content} for message in messages]  # Convert messages to JSON format
    return JsonResponse(data, safe=False)  # Return JSON response with messages