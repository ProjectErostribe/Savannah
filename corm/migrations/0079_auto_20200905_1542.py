# Generated by Django 3.0.4 on 2020-09-05 15:42

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('corm', '0078_managerprofile'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='managerprofile',
            options={'ordering': ('-last_seen',)},
        ),
        migrations.AddField(
            model_name='community',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]