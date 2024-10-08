# Generated by Django 4.2.2 on 2023-08-09 15:11

from django.conf import settings
import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(blank=True, default=None, help_text='File name', max_length=200, null=True)),
                ('file', models.FileField(default=None, help_text='This is a file', storage=django.core.files.storage.FileSystemStorage(), upload_to='uploaded_files')),
                ('is_public', models.BooleanField(default=False, help_text='opt in to submit your data into example pool')),
                ('current_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
