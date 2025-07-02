from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from inventory.models import FeaturedMotorcycle
from inventory.forms.admin_featured_motorcycle_form import FeaturedMotorcycleForm

class FeaturedMotorcycleCreateUpdateView(UpdateView):
    model = FeaturedMotorcycle
    form_class = FeaturedMotorcycleForm
    template_name = "inventory/admin_featured_motorcycle_create_update.html"
    context_object_name = "featured_motorcycle"

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        if pk:
            return get_object_or_404(FeaturedMotorcycle, pk=pk)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = (
            f"Edit Featured Motorcycle: {self.object.motorcycle.title}"
            if self.object
            else "Add New Featured Motorcycle"
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            self.object = form.save()
            messages.success(self.request, "Featured motorcycle saved successfully!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Please correct the errors below.")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy("inventory:featured_motorcycles")
