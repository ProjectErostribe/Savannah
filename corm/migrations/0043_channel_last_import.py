# Generated by Django 3.0.4 on 2020-04-25 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corm', '0042_channel_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='last_import',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]