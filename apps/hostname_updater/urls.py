from django.urls import path
from . import views

urlpatterns = [
    path('update_hostname/', views.update_hostname, name='update_hostname'),
    path('manage_resources/', views.manage_resources, name='manage_resources'),
    path('zabbix_delete/', views.zabbix_delete, name='zabbix_delete'),
    path('select_zabbix_telegraf_config/', views.select_zabbix_telegraf_config, name='select_zabbix_telegraf_config'),

]
