# Generated by Django 3.0.4 on 2020-04-16 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corm', '0033_auto_20200415_2012'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='timestamp',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='conversation',
            name='timestamp',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='done',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]