# Generated by Django 5.2 on 2025-05-05 04:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='visitoreventhistory',
            name='visitor_ids',
        ),
        migrations.AddField(
            model_name='visitoreventhistory',
            name='visitors',
            field=models.ManyToManyField(related_name='event_histories', to='myapp.visitor'),
        ),
    ]
