from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from dashboard.models import Review
from dashboard.forms import ReviewForm

class ReviewCreateUpdateView(AdminRequiredMixin, View):
    """
    View to handle both creation of new reviews and updates to existing ones.
    """
    template_name = "dashboard/review_create_update.html"
    form_class = ReviewForm

    def get(self, request, pk=None, *args, **kwargs):
        if pk:
            instance = get_object_or_404(Review, pk=pk)
            form = self.form_class(instance=instance)
            page_title = "Edit Review"
        else:
            instance = None
            form = self.form_class()
            page_title = "Create Review"

        context = {
            "form": form,
            "is_edit_mode": bool(pk),
            "page_title": page_title,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        if pk:
            instance = get_object_or_404(Review, pk=pk)
            form = self.form_class(request.POST, instance=instance)
            page_title = "Edit Review"
        else:
            instance = None
            form = self.form_class(request.POST)
            page_title = "Create Review"

        if form.is_valid():
            review = form.save()
            if pk:
                messages.success(request, f"Review by '{review.author_name}' updated successfully.")
            else:
                messages.success(request, f"Review by '{review.author_name}' created successfully.")
            return redirect(reverse("dashboard:reviews_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": bool(pk),
                "page_title": page_title,
            }
            return render(request, self.template_name, context)
