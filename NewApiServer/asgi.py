
# import os
# import django
# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NewApiServer.settings')
# django.setup()
# application = get_asgi_application()



# import os
# import django
# from channels.routing import ProtocolTypeRouter
# from django.core.asgi import get_asgi_application


# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NewApiServer.settings')
# django.setup()

# from NewApiServer import routing  # Import your routing configuration

# application = ProtocolTypeRouter({
#     'http': get_asgi_application(),  # If you need HTTP support
#     'websocket': routing.application,  # Use the routing configuration from routing.py
# })
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from myapp.consumers import NotificationConsumer
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NewApiServer.settings')
django.setup()
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/visitor_track/notifications/<group_name>/', NotificationConsumer.as_asgi()),
        ])
    ),
})
