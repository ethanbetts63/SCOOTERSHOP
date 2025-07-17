from django.urls import path
from dashboard.views import (
    DashboardIndexView,
    SettingsBusinessInfoView,
    SettingsVisibilityView,
    ClearNotificationsView,
    ReviewsManagementView,
    ReviewCreateUpdateView,
    ReviewDetailsView,
    ReviewDeleteView,
    AutopopulateReviewsView,
    GoogleMyBusinessSettingsView,
    GoogleMyBusinessAuthView,
    GoogleMyBusinessCallbackView,
    GoogleMyBusinessDisconnectView,
)

from dashboard.ajax.search_google_reviews import search_google_reviews_ajax

app_name = "dashboard"

urlpatterns = [
    path("", DashboardIndexView.as_view(), name="dashboard_index"),
    path(
        "notifications/clear/",
        ClearNotificationsView.as_view(),
        name="clear_notifications",
    ),
    path(
        "settings/business-info/",
        SettingsBusinessInfoView.as_view(),
        name="settings_business_info",
    ),
    path(
        "settings/visibility/",
        SettingsVisibilityView.as_view(),
        name="settings_visibility",
    ),
    # Review Management URLs
    path("reviews/", ReviewsManagementView.as_view(), name="reviews_management"),
    path("reviews/create/", ReviewCreateUpdateView.as_view(), name="review_create"),
    path(
        "reviews/autopopulate/",
        AutopopulateReviewsView.as_view(),
        name="autopopulate_reviews",
    ),
    path("reviews/<int:pk>/", ReviewDetailsView.as_view(), name="review_details"),
    path("reviews/<int:pk>/delete/", ReviewDeleteView.as_view(), name="review_delete"),
    path(
        "ajax/search-google-reviews/",
        search_google_reviews_ajax,
        name="search_google_reviews_ajax",
    ),
    path("settings/gmb/", GoogleMyBusinessSettingsView.as_view(), name="gmb_settings"),
    path("gmb/auth/", GoogleMyBusinessAuthView.as_view(), name="gmb_auth"),
    path("gmb/callback/", GoogleMyBusinessCallbackView.as_view(), name="gmb_callback"),
    path(
        "gmb/disconnect/",
        GoogleMyBusinessDisconnectView.as_view(),
        name="gmb_disconnect",
    ),
]
