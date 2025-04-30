# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from camera.consumers import NotificationConsumer
# from django.urls import path
# from django.core.asgi import get_asgi_application
# from channels.security.websocket import AllowedHostsOriginValidator


# application = ProtocolTypeRouter({
#     'websocket': AllowedHostsOriginValidator(
#         AuthMiddlewareStack(
#             URLRouter(
#                 [
#                 path('ws/notifications/', NotificationConsumer.as_asgi()),
#                 ]
#             )
#         )
#     ),
# })

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from myapp.consumers import NotificationConsumer
from django.urls import path

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/visitor_track/notifications/<group_name>/', NotificationConsumer.as_asgi()),
            
        ])
    ),
})
