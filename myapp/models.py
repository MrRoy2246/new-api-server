from django.db import models

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

    full_name = models.CharField(max_length=100) #required
    email = models.EmailField() #required
    phone_number = models.CharField(max_length=20) #required
    company_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='other') #required
    identification_type = models.CharField(max_length=10, choices=IDENTIFICATION_CHOICES,null=True, blank=True)
    identification_number = models.CharField(max_length=50,null=True, blank=True)
    photo = models.ImageField(upload_to='visitor_photos/', null=True, blank=True) #required
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    track_status = models.BooleanField(default=False) 
    
    # ✅ Timestamps
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 


    def __str__(self):
        return f"{self.full_name} ({self.identification_type.upper()} - {self.identification_number})"
