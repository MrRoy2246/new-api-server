# Generated by Django 5.2 on 2025-04-17 05:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_auto_20250415_1753'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitor',
            name='gender',
            field=models.CharField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], default='other', max_length=10),
        ),
    ]
