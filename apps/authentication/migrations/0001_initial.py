# Generated by Django 4.2.15 on 2024-11-05 03:31

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PagePermissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('can_access_update_hostname', 'Can access Update Hostname page'), ('can_access_manage_resources', 'Can access Manage Resources page'), ('can_access_zabbix_delete', 'Can access Zabbix Delete page'), ('can_access_select_zabbix_telegraf_config', 'Can access Select Zabbix Telegraf Config page'), ('can_access_manage_brands_trackers', 'Can access Manage Brands Trackers page'), ('can_access_json_filter_view', 'Can access JSON Filter View page')],
            },
        ),
    ]