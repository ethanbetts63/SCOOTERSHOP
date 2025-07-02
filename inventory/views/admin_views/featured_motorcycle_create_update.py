from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.models import FeaturedMotorcycle
from inventory.forms.admin_featured_motorcycle_form import FeaturedMotorcycleForm

class FeaturedMotorcycleCreateView(CreateView):
    model = FeaturedMotorcycle
    form_class = FeaturedMotorcycleForm
    template_name = "dashboard/featured_motorcycle_create.html"
    success_url = reverse_lazy("dashboard:featured_motorcycles")

    def get_initial(self):
        initial = super().get_initial()
        category = self.request.GET.get('category')
        if category:
            initial['category'] = category
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add New Featured Motorcycle"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Featured motorcycle added successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
