from django.urls import path
from . import views
from .views import Refunds


app_name = "payments"

urlpatterns = [
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),
    path(
        "refund/request/",
        Refunds.UserRefundRequestView.as_view(),
        name="user_refund_request",
    ),
    path(
        "refund/request/confirmation/",
        Refunds.UserConfirmationRefundRequestView.as_view(),
        name="user_confirmation_refund_request",
    ),
    path(
        "refund/verified/",
        Refunds.UserVerifiedRefundView.as_view(),
        name="user_verified_refund",
    ),
    path(
        "refund/verify/",
        Refunds.UserVerifyRefundView.as_view(),
        name="user_verify_refund",
    ),
    path(
        "settings/refunds/",
        Refunds.AdminRefundManagement.as_view(),
        name="admin_refund_management",
    ),
    path(
        "settings/refunds/add/",
        Refunds.AdminAddEditRefundRequestView.as_view(),
        name="add_refund_request",
    ),
    path(
        "settings/refunds/edit/<int:pk>/",
        Refunds.AdminAddEditRefundRequestView.as_view(),
        name="edit_refund_request",
    ),
    path(
        "settings/refunds/process/<int:pk>/",
        Refunds.ProcessRefundView.as_view(),
        name="process_refund",
    ),
    path(
        "settings/refunds/reject/<int:pk>/",
        Refunds.AdminRejectRefundView.as_view(),
        name="reject_refund_request",
    ),
    path(
        "admin/refund-policy-settings/",
        Refunds.admin_refund_settings_view.AdminRefundSettingsView.as_view(),
        name="admin_refund_settings",
    ),
    path(
        "settings/refunds/initiate-process/<int:pk>/",
        Refunds.IntermediaryRefundProcessingView.as_view(),
        name="initiate_refund_process",
    ),
    path('dashboard/terms/refunds/', Refunds.AdminRefundTermsManagementView.as_view(), name='refund_terms_management'),
    path('dashboard/terms/refunds/create/', Refunds.AdminRefundTermsCreateView.as_view(), name='refund_terms_create'),
    path('dashboard/terms/refunds/<int:pk>/', Refunds.AdminRefundTermsDetailsView.as_view(), name='refund_terms_details'),
]
