from django.contrib import admin
from .models import Visitor,VisitorEventHistory

admin.site.register(Visitor)
admin.site.register(VisitorEventHistory)