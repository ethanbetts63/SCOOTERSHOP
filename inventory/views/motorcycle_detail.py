# inventory/views/motorcycle_detail.py

from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy # Import reverse_lazy for success_url
from django.contrib import messages # Import messages

# Import models from the inventory app
from inventory.models import Motorcycle, MotorcycleImage
# Import forms from the inventory app
from inventory.forms import MotorcycleForm, MotorcycleImageFormSet
# Import utility function from the inventory app
from inventory.utils import get_featured_motorcycles


# Displays detailed information about a specific motorcycle
class MotorcycleDetailView(DetailView):
    model = Motorcycle
    # Updated template path
    template_name = 'inventory/motorcycles/motorcycle_detail.html'
    context_object_name = 'motorcycle' # Use 'motorcycle' for consistency

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add additional images to context
        additional_images = self.object.images.all()
        context['additional_images'] = additional_images

        # Determine which condition to use for featured motorcycles
        # Use the first condition associated with the motorcycle for simplicity in featured logic
        # Safely access condition name
        motorcycle_condition_name = self.object.conditions.first().name if self.object.conditions.first() else None

        featured_condition = motorcycle_condition_name.lower() if motorcycle_condition_name else None

        # Special case: For demo bikes, show used featured listings (handled in get_featured_motorcycles)


        # Get featured motorcycles with the appropriate condition
        featured = get_featured_motorcycles(
            exclude_id=self.object.pk,
            limit=3,
            condition=featured_condition # Pass the determined condition
        )

        context['featured_motorcycles'] = featured

        # Set the appropriate condition in the context for the template
        # This determines which "View All" link to show
        # Pass the original case condition name if available
        context['condition'] = motorcycle_condition_name
        # Pass the lowercase for comparison in templates
        context['condition_lower'] = featured_condition


        # Define specifications with their labels and icons
        motorcycle = self.object
        specifications = [
            {'field': 'condition', 'label': 'Condition', 'icon': 'icon-category', 'value': ", ".join([c.get_name_display() for c in motorcycle.conditions.all()]) if motorcycle.conditions.exists() else None}, # Display all conditions, handle no conditions
            {'field': 'year', 'label': 'Year', 'icon': 'icon-year', 'value': motorcycle.year},
            {'field': 'odometer', 'label': 'Odometer', 'icon': 'icon-odometer', 'value': f"{motorcycle.odometer} km" if motorcycle.odometer is not None else None},
            {'field': 'engine_size', 'label': 'Engine', 'icon': 'icon-capacity', 'value': f"{motorcycle.engine_size}cc" if motorcycle.engine_size else None},
            {'field': 'seats', 'label': 'Seats', 'icon': 'icon-seat', 'value': motorcycle.seats},
            {'field': 'transmission', 'label': 'Transmission', 'icon': 'icon-transmission', 'value': motorcycle.transmission},
            {'field': 'rego', 'label': 'Registration', 'icon': 'icon-rego', 'value': motorcycle.rego},
            {'field': 'rego_exp', 'label': 'Rego Expires', 'icon': 'icon-rego-exp', 'value': motorcycle.rego_exp.strftime("%d %b %Y") if motorcycle.rego_exp else None},
            {'field': 'stock_number', 'label': 'Stock #', 'icon': 'icon-stock', 'value': motorcycle.stock_number},
            # Add daily_hire_rate if it's a hire bike
             {'field': 'daily_hire_rate', 'label': 'Daily Hire Rate', 'icon': 'icon-money', 'value': f"${motorcycle.daily_hire_rate:.2f}" if motorcycle.daily_hire_rate is not None and is_for_hire else None},
        ]

        # Determine if the motorcycle has the 'hire' or 'new' condition for filtering specs
        is_for_hire = self.object.conditions.filter(name='hire').exists()
        is_new = self.object.conditions.filter(name='new').exists()

        # Filter out specs based on condition and None values
        filtered_specifications = [
            spec for spec in specifications
            if spec['value'] is not None and (
                (is_for_hire and spec['field'] not in ['stock_number', 'rego_exp', 'rego', 'odometer']) or
                (is_new and spec['field'] not in ['stock_number', 'rego_exp', 'rego']) or
                (not is_for_hire and not is_new) # For used/demo/other, include all non-None
            )
        ]


        context['filtered_specifications'] = filtered_specifications

        return context


class MotorcycleFormHandlerMixin:
    """Mixin to handle saving the main form and the image formset."""
    def form_valid(self, form):
        context = self.get_context_data()
        images_formset = context['images_formset']

        # First save the main form to get an instance
        self.object = form.save()

        # Handle multiple uploaded files for the 'additional_images' input
        # Note: This input is separate from the formset
        additional_images = self.request.FILES.getlist('additional_images')
        for image_file in additional_images:
            if image_file:  # Make sure there's actually a file
                MotorcycleImage.objects.create(
                    motorcycle=self.object,
                    image=image_file
                )

        # Process the formset for existing images (for deletions and changes)
        # Check if the formset has data before processing
        if images_formset.has_changed() or images_formset.is_valid():
             images_formset.instance = self.object # Link the formset to the saved motorcycle
             images_formset.save()
        elif images_formset.errors:
             # If formset has errors but no changes were made, log/handle appropriately
             print(f"Image formset had errors but no changes detected: {images_formset.errors}")
             # You might want to add messages.error here or handle in form_invalid


        return super().form_valid(form)

    def form_invalid(self, form):
        # Include formset in context when the main form is invalid
        context = self.get_context_data()
        context['form'] = form # Ensure the invalid main form is in context
        # The formset is already added in get_context_data if request is POST

        # Add formset errors to messages if any
        if 'images_formset' in context and context['images_formset'].errors:
             # Iterate through formset errors and add to messages
             for error_dict in context['images_formset'].errors:
                 for field, errors in error_dict.items():
                      for error in errors:
                           messages.error(self.request, f"Image form error - {field}: {error}")
             # Add non-field errors for the formset itself
             for error in context['images_formset'].non_form_errors():
                  messages.error(self.request, f"Image formset error: {error}")


        return render(self.request, self.template_name, context)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            # If POST, populate formset with data
            context['images_formset'] = MotorcycleImageFormSet(self.request.POST, self.request.FILES, instance=self.object if hasattr(self, 'object') else None)
        else:
            # If GET, populate formset with existing images if object exists
            context['images_formset'] = MotorcycleImageFormSet(instance=self.object if hasattr(self, 'object') else None)
        return context


class MotorcycleCreateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, CreateView):
    model = Motorcycle
    form_class = MotorcycleForm
    # Updated template path
    template_name = 'inventory/motorcycles/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        # Only staff can create motorcycles
        return self.request.user.is_staff

    def form_valid(self, form):
        # Assign the logged-in user as the seller (assuming seller field exists and is a ForeignKey to User)
        # If you have a seller field and want the creating staff user to be the seller, uncomment this:
        # form.instance.seller = self.request.user

        messages.success(self.request, "Motorcycle added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to the detail page of the newly created motorcycle using the inventory namespace
        return reverse_lazy('inventory:motorcycle-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create_view'] = True # Helps in template logic (e.g., button text)
        context['page_title'] = 'Add New Motorcycle' # Set page title
        return context


class MotorcycleUpdateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, UpdateView):
    model = Motorcycle
    form_class = MotorcycleForm
    # Updated template path
    template_name = 'inventory/motorcycles/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        # Only staff can update motorcycles
        # Original check: motorcycle = self.get_object(); return self.request.user == motorcycle.seller
        # Assuming staff are the only ones who manage inventory, the is_staff check is sufficient.
        return self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, "Motorcycle updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to the detail page of the updated motorcycle using the inventory namespace
        return reverse_lazy('inventory:motorcycle-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update_view'] = True # Helps in template logic (e.g., button text)
        context['page_title'] = f'Edit {self.object.year} {self.object.brand} {self.object.model}' # Set page title
        return context


# Handles deletion of motorcycle listings
class MotorcycleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Motorcycle
    # Updated template path
    template_name = 'inventory/motorcycles/motorcycle_confirm_delete.html'
    # Redirect to index or motorcycle list after deletion
    # Using 'core:index' assuming the core app will be namespaced as 'core'
    success_url = reverse_lazy('core:index')

    def test_func(self):
        # Only staff can delete motorcycles
        # Original check: motorcycle = self.get_object(); return self.request.user == motorcycle.seller
        # Assuming staff are the only ones who manage inventory, the is_staff check is sufficient.
        return self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, f"Motorcycle '{self.get_object()}' deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Delete Motorcycle' # Set page title
        return context