# chat/urls.py

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('chat_room/', views.chat_room, name='chat_room'),
    path('start-chat/<str:username>/', views.start_chat, name='start_chat'),
    path('send-message/<str:username>/', views.send_message, name='send_message'),
    path('edit_message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('delete_message/<int:message_id>/', views.delete_message, name='delete_message'),
    path('profile/', views.profile, name='profile'),
    path('facial_login/', views.facial_login, name='facial_login'),
    path('ask/', views.ask_question, name='ask_question'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
