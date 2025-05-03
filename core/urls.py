# SCOOTER_SHOP/core/urls.py

from django.urls import path
# Import only the views needed for core pages
from .views import index, service, about, contact, privacy, returns, security, terms

app_name = 'core' # Set the app name for namespacing

urlpatterns = [
    # --- Main Site Pages ---
    path('', index, name='index'),
    # Decide if 'service' page belongs here or in the 'service' app.
    # Since it seems to be a general info page about service, let's keep it here for now.
    path('service', service, name='service'),

    # --- Information Pages ---
    path('about', about, name='about'),
    path('contact', contact, name='contact'),
    path('privacy', privacy, name='privacy'),
    path('returns', returns, name='returns'),
    path('security', security, name='security'),
    path('terms', terms, name='terms'),

    # --- Include features --- 
    path('featured/', views.featured_view, name='featured'),
    path('map/', views.map_view, name='map'),
    path('reviews/', views.reviews_view, name='reviews'),
]