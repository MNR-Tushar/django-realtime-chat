from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ws://127.0.0.1:8000/ws/chat/general/ → ChatConsumer
    re_path(
        r'ws/chat/(?P<room_slug>[\w-]+)/$',
        consumers.ChatConsumer.as_asgi()
    ),
]