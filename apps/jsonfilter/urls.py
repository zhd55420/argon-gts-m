from django.urls import path
from .views import json_filter_view

urlpatterns = [
    path('jsonfilter/', json_filter_view, name='json_filter'),
]
