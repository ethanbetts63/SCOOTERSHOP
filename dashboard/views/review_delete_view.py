from django.views.generic import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from django.shortcuts import redirect

from dashboard.models import Review


class ReviewDeleteView(AdminRequiredMixin, DeleteView):
    model = Review
    success_url = reverse_lazy("dashboard:reviews_management")

    def form_valid(self, form):
        messages.success(
            self.request,
            f"The review by '{self.object.author_name}' was deleted successfully.",
        )
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        return redirect(self.success_url)
