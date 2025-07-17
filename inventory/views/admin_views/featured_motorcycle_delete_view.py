from inventory.mixins import AdminRequiredMixin
from django.views.generic import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.models import FeaturedMotorcycle


class FeaturedMotorcycleDeleteView(AdminRequiredMixin, DeleteView):
    model = FeaturedMotorcycle
    success_url = reverse_lazy("inventory:featured_motorcycles")

    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Featured motorcycle removed successfully!")
        return super().post(request, *args, **kwargs)
