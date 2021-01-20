# Generated by Django 3.0.4 on 2020-12-28 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corm', '0088_auto_20201210_1826'),
    ]

    operations = [
        migrations.AddField(
            model_name='userauthcredentials',
            name='auth_refresh',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='threshold_user',
            field=models.SmallIntegerField(default=1, help_text='Number of conversations needed to become a Visitor', verbose_name='Visitor level'),
        ),
        migrations.AlterField(
            model_name='source',
            name='connector',
            field=models.CharField(choices=[('corm.plugins.null', 'Manual Entry'), ('corm.plugins.api', 'API'), ('corm.plugins.reddit', 'Reddit'), ('corm.plugins.twitter', 'Twitter'), ('corm.plugins.discourse', 'Discourse'), ('corm.plugins.slack', 'Slack'), ('corm.plugins.discord', 'Discord'), ('corm.plugins.github', 'Github'), ('corm.plugins.gitlab', 'Gitlab'), ('corm.plugins.stackexchange', 'Stack Exchange'), ('corm.plugins.rss', 'RSS'), ('corm.plugins.reddit', 'Reddit')], max_length=256),
        ),
        migrations.AlterField(
            model_name='userauthcredentials',
            name='connector',
            field=models.CharField(choices=[('corm.plugins.null', 'Manual Entry'), ('corm.plugins.api', 'API'), ('corm.plugins.reddit', 'Reddit'), ('corm.plugins.twitter', 'Twitter'), ('corm.plugins.discourse', 'Discourse'), ('corm.plugins.slack', 'Slack'), ('corm.plugins.discord', 'Discord'), ('corm.plugins.github', 'Github'), ('corm.plugins.gitlab', 'Gitlab'), ('corm.plugins.stackexchange', 'Stack Exchange'), ('corm.plugins.rss', 'RSS'), ('corm.plugins.reddit', 'Reddit')], max_length=256),
        ),
    ]