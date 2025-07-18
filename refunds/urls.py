from django.urls import path
from .views.user_views import (
    UserRefundRequestView,
    UserConfirmationRefundRequestView,
    UserVerifiedRefundView,
    UserVerifyRefundView,
    RefundTermsView,
)

from .views.admin_views import (
    AdminRefundManagement,
    AdminCreateRefundRequestView,
    AdminEditRefundRequestView,
    ProcessRefundView,
    AdminRejectRefundView,
    admin_refund_settings_view,
    IntermediaryRefundProcessingView,
    AdminRefundTermsManagementView,
    AdminRefundTermsCreateView,
    AdminRefundTermsDetailView,
)
from .ajax import ajax_get_booking_details

app_name = "refunds"

urlpatterns = [
    path(
        "refund/request/",
        UserRefundRequestView.as_view(),
        name="user_refund_request",
    ),
    path(
        "refund/request/confirmation/",
        UserConfirmationRefundRequestView.as_view(),
        name="user_confirmation_refund_request",
    ),
    path(
        "refund/verified/",
        UserVerifiedRefundView.as_view(),
        name="user_verified_refund",
    ),
    path(
        "refund/verify/",
        UserVerifyRefundView.as_view(),
        name="user_verify_refund",
    ),
    path(
        "settings/refunds/",
        AdminRefundManagement.as_view(),
        name="admin_refund_management",
    ),
    path(
        "settings/refunds/add/",
        AdminCreateRefundRequestView.as_view(),
        name="add_refund_request",
    ),
    path(
        "settings/refunds/edit/<int:pk>/",
        AdminEditRefundRequestView.as_view(),
        name="edit_refund_request",
    ),
    path(
        "settings/refunds/process/<int:pk>/",
        ProcessRefundView.as_view(),
        name="process_refund",
    ),
    path(
        "settings/refunds/reject/<int:pk>/",
        AdminRejectRefundView.as_view(),
        name="reject_refund_request",
    ),
    path(
        "admin/refund-policy-settings/",
        admin_refund_settings_view.AdminRefundSettingsView.as_view(),
        name="admin_refund_settings",
    ),
    path(
        "settings/refunds/initiate-process/<int:pk>/",
        IntermediaryRefundProcessingView.as_view(),
        name="initiate_refund_process",
    ),
    path(
        "dashboard/terms/refunds/",
        AdminRefundTermsManagementView.as_view(),
        name="refund_terms_management",
    ),
    path(
        "dashboard/terms/refunds/create/",
        AdminRefundTermsCreateView.as_view(),
        name="refund_terms_create",
    ),
    path(
        "dashboard/terms/refunds/<int:pk>/",
        AdminRefundTermsDetailView.as_view(),
        name="refund_terms_details",
    ),
    path("refund-policy/", RefundTermsView.as_view(), name="refund_policy"),
    path("ajax/get-booking-details/", ajax_get_booking_details.get_booking_details_by_reference, name="ajax_get_booking_details_by_reference"),
]
