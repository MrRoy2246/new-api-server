# Generated by Django 5.2 on 2025-05-06 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_visitoreventhistory_visitors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visitoreventhistory',
            name='capture_time',
            field=models.CharField(max_length=100),
        ),
    ]
