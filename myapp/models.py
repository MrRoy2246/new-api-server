from django.db import models
import uuid
class VisitorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
class Visitor(models.Model):
    IDENTIFICATION_CHOICES = [
        ('nid', 'NID'),
        ('passport', 'Passport'),
        ('driving', 'Driving License'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)  # New unique UUID field
    first_name = models.CharField(max_length=50) #required
    last_name = models.CharField(max_length=50) #required
    email = models.EmailField() #required
    phone_number = models.CharField(max_length=20) #required
    company_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='other') #required
    identification_type = models.CharField(max_length=10, choices=IDENTIFICATION_CHOICES,null=True, blank=True)
    identification_number = models.CharField(max_length=50,null=True, blank=True)
    photo = models.ImageField(upload_to='visitor_photos/') #required
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    track_status = models.BooleanField(default=False) 
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 
    objects = VisitorManager()
    all_objects = models.Manager()
    def __str__(self):
        return f"{self.full_name}"
    def soft_delete(self):
        self.is_deleted = True
        # self.track_status = False
        self.save()
    def restore(self):
        self.is_deleted = False
        self.save()
