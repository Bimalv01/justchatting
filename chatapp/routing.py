# # project/routing.py

# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.urls import path
# from channels.auth import AuthMiddlewareStack
# from chat import urls as chat_urls

# application = ProtocolTypeRouter({
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             chat_urls.websocket_urlpatterns
#         )
#     ),
# })
