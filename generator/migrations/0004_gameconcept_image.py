# Generated by Django 5.2 on 2025-04-10 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0003_gameconcept_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameconcept',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='concept/'),
        ),
    ]
