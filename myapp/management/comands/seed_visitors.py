from django.core.management.base import BaseCommand
from django_seed import Seed
from myapp.models import Visitor
from faker import Faker
import random
from django.core.files.base import ContentFile
import io
from PIL import Image

fake = Faker()

class Command(BaseCommand):
    help = 'Seed the database with dummy Visitors'

    def handle(self, *args, **kwargs):
        seeder = Seed.seeder()

        # Required choices
        genders = [choice[0] for choice in Visitor.GENDER_CHOICES]
        id_types = [choice[0] for choice in Visitor.IDENTIFICATION_CHOICES]

        def get_dummy_image():
            # Create a simple black image as a placeholder
            img = Image.new("RGB", (100, 100), color=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            return ContentFile(buffer.getvalue(), name=f"{fake.first_name()}.jpg")

        for _ in range(10):
            visitor = Visitor(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone_number=fake.phone_number(),
                company_name=fake.company(),
                gender=random.choice(genders),
                identification_type=random.choice(id_types),
                identification_number=fake.ssn(),
                photo=get_dummy_image(),
                entry_time=fake.date_time_this_year(),
                exit_time=fake.date_time_this_year(),
                note=fake.sentence(),
                track_status=random.choice([True, False])
            )
            visitor.save()

        self.stdout.write(self.style.SUCCESS("✅ 10 dummy visitors created successfully."))
