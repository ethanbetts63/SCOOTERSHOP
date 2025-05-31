# payments/urls.py
from django.urls import path
from . import views
from .views.HireRefunds import utils as hire_refund_utils # Import the new utils file

app_name = 'payments'

urlpatterns = [
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    # New URL for fetching hire booking details via AJAX
    path('api/hire-booking-details/<int:pk>/', hire_refund_utils.get_hire_booking_details_json, name='api_hire_booking_details'),
]
