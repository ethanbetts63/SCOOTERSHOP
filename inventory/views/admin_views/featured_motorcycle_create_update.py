from inventory.mixins import AdminRequiredMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from inventory.models import FeaturedMotorcycle, Motorcycle
from inventory.forms.admin_featured_motorcycle_form import FeaturedMotorcycleForm

class FeaturedMotorcycleCreateUpdateView(AdminRequiredMixin, UpdateView):
    model = FeaturedMotorcycle
    form_class = FeaturedMotorcycleForm
    template_name = "inventory/admin_featured_motorcycle_create_update.html"
    context_object_name = "featured_motorcycle"

    def get_object(self, queryset=None):
        """
        Returns the FeaturedMotorcycle instance that the view is displaying.
        For new instances, returns None.
        """
        pk = self.kwargs.get("pk")
        if pk:
            return get_object_or_404(FeaturedMotorcycle, pk=pk)
        return None

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        Sets the 'category' from the URL parameter if present.
        """
        initial = super().get_initial()
        category = self.request.GET.get('category')
        if category:
            initial['category'] = category
        return initial

    def get_context_data(self, **kwargs):
        """
        Inserts additional context into the template.
        """
        context = super().get_context_data(**kwargs)
        self.object = self.get_object()

        # Determine the motorcycle condition ('new' or 'used')
        motorcycle_condition = self.request.GET.get('category')
        if self.object:
            motorcycle_condition = self.object.category
        
        context["title"] = (
            f"Edit Featured {motorcycle_condition.title()} Motorcycle"
            if self.object
            else f"Add New Featured {motorcycle_condition.title()} Motorcycle"
        )
        context["motorcycle_condition"] = motorcycle_condition
        
        # Pass the currently selected motorcycle if editing
        if self.object:
            context["selected_motorcycle"] = self.object.motorcycle

        # URLs for AJAX calls in the template
        context["ajax_search_motorcycles_url"] = reverse("inventory:admin_api_search_motorcycles")
        context["ajax_get_motorcycle_details_url"] = reverse("inventory:admin_api_get_motorcycle_details", kwargs={'pk': 0}).replace('0', '')


        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then validating it.
        """
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            self.object = form.save()
            messages.success(self.request, "Featured motorcycle saved successfully!")
            return redirect(self.get_success_url())
        else:
            # Re-render the form with validation errors.
            messages.error(self.request, "Please correct the errors below.")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        """
        Returns the URL to redirect to after processing a valid form.
        """
        return reverse_lazy("inventory:featured_motorcycles")
