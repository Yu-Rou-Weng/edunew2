"""Django Url for Autogen Subsystem."""
from django.urls import path

from . import views

urlpatterns = [
    path('create_device/', views.create_device, name='create_device'),
    path('delete_device/', views.delete_device, name='delete_device'),
    path('ccm_api/', views.ccm_api, name='ccm_api'),
]
