# payments/urls.py
from django.urls import path

from ..service.ajax import ajax_get_service_booking_details
from . import views
from .views import Refunds # This already imports the HireRefunds package
from .utils import ajax_get_hire_booking_details


app_name = 'payments'

urlpatterns = [
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    # New URL for fetching hire booking details via AJAX
    path('api/hire-booking-details/<int:pk>/', ajax_get_hire_booking_details.get_hire_booking_details_json, name='api_hire_booking_details'),
    
    
    path('refund/request/', Refunds.UserRefundRequestView.as_view(), name='user_refund_request'),
    path('refund/request/confirmation/', Refunds.UserConfirmationRefundRequestView.as_view(), name='user_confirmation_refund_request'),

    # User page after clicking the verification link in email
    path('refund/verified/', Refunds.UserVerifiedRefundView.as_view(), name='user_verified_refund'),
    # URL for the email verification link (e.g., /refund/verify/?token=...)
    path('refund/verify/', Refunds.UserVerifyRefundView.as_view(), name='user_verify_refund'),

    
    path('settings/refunds/', Refunds.AdminRefundManagement.as_view(), name='admin_refund_management'),
    path('settings/refunds/add/', Refunds.AdminAddEditRefundRequestView.as_view(), name='add_refund_request'),
    path('settings/refunds/edit/<int:pk>/', Refunds.AdminAddEditRefundRequestView.as_view(), name='edit_refund_request'),
    path('settings/refunds/process/<int:pk>/', Refunds.ProcessRefundView.as_view(), name='process_refund'),
    path('settings/refunds/reject/<int:pk>/', Refunds.AdminRejectRefundView.as_view(), name='reject_refund_request'),
    path('admin/refund-policy-settings/', Refunds.admin_refund_settings_view.AdminRefundSettingsView.as_view(), name='admin_refund_settings'),

]
