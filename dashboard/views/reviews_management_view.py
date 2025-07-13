from django.views.generic import ListView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
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

    def post(self, request, *args, **kwargs):
        review_id = request.POST.get("review_id")
        action = request.POST.get("action")
        review = get_object_or_404(Review, id=review_id)

        if action == "increment":
            review.display_order += 1
            review.save()
            messages.success(request, f"Display order for review by '{review.author_name}' incremented.")
        elif action == "decrement":
            if review.display_order > 0:
                review.display_order -= 1
                review.save()
                messages.success(request, f"Display order for review by '{review.author_name}' decremented.")
            else:
                messages.warning(request, "Display order cannot be less than 0.")
        
        return redirect(reverse("dashboard:reviews_management"))
