from rest_framework import serializers
from .models import Visitor

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = [
            'id',
            'uid',
            'full_name',
            'email',
            'phone_number',
            'company_name',
            'gender',
            'identification_type',
            'identification_number',
            'photo',
            'entry_time',
            'exit_time',
            'note',
            'track_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uid', 'created_at', 'updated_at']

    def validate_email(self, value):
        # Exclude self when updating
        instance = self.instance
        if Visitor.all_objects.filter(email=value, is_deleted=False).exclude(pk=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError("A visitor with this email already exists.")
        return value

    def validate_phone_number(self, value):
        # Exclude self when updating
        instance = self.instance
        if Visitor.all_objects.filter(phone_number=value, is_deleted=False).exclude(pk=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError("A visitor with this phone number already exists.")
        return value

