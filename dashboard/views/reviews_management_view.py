from django.views.generic import ListView
from inventory.mixins import AdminRequiredMixin
from dashboard.models import Review

class ReviewsManagementView(AdminRequiredMixin, ListView):
    """
    View to list all curated reviews for the admin.
    """
    model = Review
    template_name = "dashboard/reviews_management.html"
    context_object_name = "reviews"
    paginate_by = 15

    def get_queryset(self):
        return Review.objects.all().order_by('display_order', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Display Reviews Management"
        return context
