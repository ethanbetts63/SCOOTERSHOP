from django.views.generic import DetailView
from inventory.mixins import AdminRequiredMixin
from dashboard.models import Review

class ReviewDetailsView(AdminRequiredMixin, DetailView):
    model = Review
    template_name = "dashboard/review_details.html"
    context_object_name = "review"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Review Details: {self.object.author_name}"
        return context
