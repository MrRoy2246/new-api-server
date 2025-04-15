from django.db import models

class Visitor(models.Model):
    IDENTIFICATION_CHOICES = [
        ('nid', 'NID'),
        ('passport', 'Passport'),
        ('driving', 'Driving License'),
    ]

    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    identification_type = models.CharField(max_length=10, choices=IDENTIFICATION_CHOICES)
    identification_number = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='visitor_photos/', null=True, blank=True)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    track_status = models.BooleanField(default=False)  # True = Tracked, False = Untracked
    
    # ✅ Timestamps
    created_at = models.DateTimeField(auto_now_add=True)  # Set once at creation
    updated_at = models.DateTimeField(auto_now=True)      # Set every time model is saved


    def __str__(self):
        return f"{self.full_name} ({self.identification_type.upper()} - {self.identification_number})"
