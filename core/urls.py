# SCOOTER_SHOP/core/urls.py

from django.urls import path
# Import only the views needed for core pages from the views package
from .views import index, about, contact, privacy, returns, security, terms

app_name = 'core' # Set the app name for namespacing

urlpatterns = [
    # --- Main Site Pages ---
    path('', index, name='index'),

    # --- Information Pages ---
    path('about', about, name='about'),
    path('contact', contact, name='contact'),
    path('privacy', privacy, name='privacy'),
    path('returns', returns, name='returns'),
    path('security', security, name='security'),
    path('terms', terms, name='terms'),

]