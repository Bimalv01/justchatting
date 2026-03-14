import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatapp.settings')

# Must import Django ASGI app before importing channels routing
# so that Django is fully set up before models/apps are loaded.
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat import routing as chat_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat_routing.websocket_urlpatterns
        )
    ),
})
