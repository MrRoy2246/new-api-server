from django.contrib import admin
from .models import Visitor,VisitorEventHistory,Camera

admin.site.register(Visitor)
admin.site.register(VisitorEventHistory)
admin.site.register(Camera)