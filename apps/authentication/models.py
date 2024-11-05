# models.py
from django.db import models

class PagePermissions(models.Model):
    class Meta:
        permissions = [
            ("can_access_update_hostname", "Can access Update Hostname page"),
            ("can_access_manage_resources", "Can access Manage Resources page"),
            ("can_access_zabbix_delete", "Can access Zabbix Delete page"),
            ("can_access_select_zabbix_telegraf_config", "Can access Select Zabbix Telegraf Config page"),
            ("can_access_manage_brands_trackers", "Can access Manage Brands Trackers page"),
            ("can_access_json_filter_view", "Can access JSON Filter View page"),
        ]