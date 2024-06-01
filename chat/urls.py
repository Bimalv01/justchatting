# chat/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('chat_room/', views.chat_room, name='chat_room'),
    path('start-chat/<str:username>/', views.start_chat, name='start_chat'),
    path('send-message/<str:username>/', views.send_message, name='send_message'),
    path('edit_message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('delete_message/<int:message_id>/', views.delete_message, name='delete_message'),
]

