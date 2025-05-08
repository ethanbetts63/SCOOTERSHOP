# SCOOTER_SHOP/core/urls.py

from django.urls import path
# Import only the views needed for core pages from the views package
from .views import index, contact, privacy_policy, returns_policy, security_policy, terms_of_use

app_name = 'core' # Set the app name for namespacing

urlpatterns = [
    # --- Main Site Pages ---
    path('', index, name='index'),

    # --- Information Pages ---
    path('contact', contact, name='contact'),
    path('privacy', privacy_policy, name='privacy'),
    path('returns', returns_policy, name='returns'),
    path('security', security_policy, name='security'),
    path('terms', terms_of_use, name='terms'),

]