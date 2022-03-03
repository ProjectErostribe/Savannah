# Generated by Django 3.1.2 on 2021-09-16 21:09

import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontendv2', '0006_publicdashboard_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='managerinvite',
            name='role',
            field=models.SmallIntegerField(choices=[(0, 'Restricted'), (1, 'Contributor'), (2, 'Manager'), (3, 'Owner')], default=1),
        ),
        migrations.AlterField(
            model_name='publicdashboard',
            name='filters',
            field=models.JSONField(default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
        migrations.AlterField(
            model_name='publicdashboard',
            name='page',
            field=models.CharField(choices=[('overview', 'Overview'), ('members', 'Members'), ('conversations', 'Conversations'), ('contributions', 'Contributions'), ('contributors', 'Contributors')], max_length=32),
        ),
        migrations.AlterField(
            model_name='publicdashboard',
            name='pin_time',
            field=models.BooleanField(default=False, help_text='Show data from the time the dashboard was shared, not the time it was viewed.'),
        ),
    ]
