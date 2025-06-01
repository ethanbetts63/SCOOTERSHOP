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
    path('refund/request/confirmation/', HireRefunds.UserConfirmationRefundRequestView.as_view(), name='user_confirmation_refund_request'),

    # User page after clicking the verification link in email
    path('refund/verified/', HireRefunds.UserVerifiedRefundView.as_view(), name='user_verified_refund'),
    # URL for the email verification link (e.g., /refund/verify/?token=...)
    path('refund/verify/', HireRefunds.UserVerifyRefundView.as_view(), name='user_verify_refund'),
]
