# SCOOTER_SHOP/core/urls.py

from django.urls import path
# Import only the views needed for core pages from the views package
from .views import index, service, about, contact, privacy, returns, security, terms

app_name = 'core' # Set the app name for namespacing

urlpatterns = [
    # --- Main Site Pages ---
    path('', index, name='index'),
    # The 'service' page remains here as a general information page about services.
    # The actual booking flow is handled in the 'service' app.
    path('service', service, name='service'),

    # --- Information Pages ---
    path('about', about, name='about'),
    path('contact', contact, name='contact'),
    path('privacy', privacy, name='privacy'),
    path('returns', returns, name='returns'),
    path('security', security, name='security'),
    path('terms', terms, name='terms'),

]