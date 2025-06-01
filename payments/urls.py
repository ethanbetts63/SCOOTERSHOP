# payments/urls.py
from django.urls import path
from . import views
from .views import HireRefunds


app_name = 'payments'

urlpatterns = [
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    # New URL for fetching hire booking details via AJAX
    path('api/hire-booking-details/<int:pk>/', HireRefunds.utils.get_hire_booking_details_json, name='api_hire_booking_details'),
    path('refund/request/', HireRefunds.UserRefundRequestView.as_view(), name='user_refund_request_hire'),
]
