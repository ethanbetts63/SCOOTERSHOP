from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from dashboard.forms import ReviewForm

class ReviewCreateUpdateView(AdminRequiredMixin, View):
    """
    View to handle creation of new reviews.
    """
    template_name = "dashboard/review_create_update.html"
    form_class = ReviewForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        page_title = "Add Review"

        context = {
            "form": form,
            "is_edit_mode": False,
            "page_title": page_title,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        page_title = "Add Review"

        if form.is_valid():
            review = form.save()
            messages.success(request, f"Review by '{review.author_name}' created successfully.")
            return redirect(reverse("dashboard:reviews_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": False,
                "page_title": page_title,
            }
            return render(request, self.template_name, context)
