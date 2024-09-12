# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path, include
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),


# 动态展示 Zabbix 和 Grafana

    # # Matches any html file
    # re_path(r'^.*\.*', views.pages, name='pages'),

    path('hostname_updater/', include('apps.hostname_updater.urls')),

]


