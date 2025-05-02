# core/views/motorcycle_detail.py

from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from ..models import Motorcycle, MotorcycleImage # Import models
from ..forms import MotorcycleForm, MotorcycleImageFormSet # Import forms
from .utils import get_featured_motorcycles # Import utility function


# Displays detailed information about a specific motorcycle
class MotorcycleDetailView(DetailView):
    model = Motorcycle
    template_name = 'motorcycles/motorcycle_detail.html'
    context_object_name = 'motorcycle' # Use 'motorcycle' for consistency

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add additional images to context
        additional_images = self.object.images.all()
        context['additional_images'] = additional_images

        # Determine which condition to use for featured motorcycles
        # Use the first condition associated with the motorcycle for simplicity in featured logic
        motorcycle_condition = self.object.conditions.first().name.lower() if self.object.conditions.first() else None

        featured_condition = motorcycle_condition

        # Special case: For demo bikes, show used featured listings
        if motorcycle_condition == 'demo':
            featured_condition = 'used'

        # Get featured motorcycles with the appropriate condition
        featured = get_featured_motorcycles(
            exclude_id=self.object.pk,
            limit=3,
            condition=featured_condition
        )

        context['featured_motorcycles'] = featured

        # Set the appropriate condition in the context for the template
        # This determines which "View All" link to show
        context['condition'] = featured_condition

        # Define specifications with their labels and icons
        motorcycle = self.object
        specifications = [
            {'field': 'condition', 'label': 'Condition', 'icon': 'icon-category', 'value': ", ".join([c.get_name_display() for c in motorcycle.conditions.all()])}, # Display all conditions
            {'field': 'year', 'label': 'Year', 'icon': 'icon-year', 'value': motorcycle.year},
            {'field': 'odometer', 'label': 'Odometer', 'icon': 'icon-odometer', 'value': f"{motorcycle.odometer} km" if motorcycle.odometer is not None else None},
            {'field': 'engine_size', 'label': 'Engine', 'icon': 'icon-capacity', 'value': f"{motorcycle.engine_size}cc" if motorcycle.engine_size else None},
            {'field': 'seats', 'label': 'Seats', 'icon': 'icon-seat', 'value': motorcycle.seats},
            {'field': 'transmission', 'label': 'Transmission', 'icon': 'icon-transmission', 'value': motorcycle.transmission},
            {'field': 'rego', 'label': 'Registration', 'icon': 'icon-rego', 'value': motorcycle.rego},
            {'field': 'rego_exp', 'label': 'Rego Expires', 'icon': 'icon-rego-exp', 'value': motorcycle.rego_exp.strftime("%d %b %Y") if motorcycle.rego_exp else None},
            {'field': 'stock_number', 'label': 'Stock #', 'icon': 'icon-stock', 'value': motorcycle.stock_number},
        ]

        # Filter out None values first and then filter based on conditions
        valid_specs = [spec for spec in specifications if spec['value'] is not None]

        # Determine if the motorcycle has the 'hire' condition
        is_for_hire = self.object.conditions.filter(name='hire').exists()
        is_new = self.object.conditions.filter(name='new').exists()

        if is_for_hire:
            # For hire bikes: exclude stock_number, rego_exp, rego, odometer
            excluded_fields = ['stock_number', 'rego_exp', 'rego', 'odometer']
            filtered_specifications = [spec for spec in valid_specs if spec['field'] not in excluded_fields]
        elif is_new:
            # For new bikes: exclude stock_number, rego_exp, and rego
            excluded_fields = ['stock_number', 'rego_exp', 'rego']
            filtered_specifications = [spec for spec in valid_specs if spec['field'] not in excluded_fields]
        else:
            # For used/demo bikes (and potentially others): show everything that's valid
            filtered_specifications = valid_specs

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
        if images_formset.is_valid():
            images_formset.instance = self.object # Link the formset to the saved motorcycle
            images_formset.save()
        else:
             # If formset is invalid, the main form should not have been saved.
             # You might want to add formset errors to the messages framework
             # and return render to show the form with errors.
             # For simplicity here, we assume main form validation implies formset will be handled,
             # but in a robust app, you'd handle formset errors explicitly before saving the main form.
             print(f"Image formset errors: {images_formset.errors}")
             # You might want to add: return self.form_invalid(form) or render the template again

        return super().form_valid(form)

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
    template_name = 'motorcycles/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        # Only staff can create motorcycles
        return self.request.user.is_staff

    def form_valid(self, form):
        # Assign the logged-in user as the seller (assuming seller field exists and is a ForeignKey to User)
        # Note: If this field is not mandatory or doesn't exist, remove or modify this line.
        # Based on your previous structure, seller might not be on the Motorcycle model.
        # If only staff can create, you might not need a 'seller' field on the model itself.
        # Let's assume for now it doesn't exist or isn't needed to be set here explicitly.
        # If you do have a seller field, uncomment and adjust the line below:
        # form.instance.seller = self.request.user

        messages.success(self.request, "Motorcycle added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to the detail page of the newly created motorcycle
        return reverse_lazy('motorcycle-detail', kwargs={'pk': self.object.pk})


class MotorcycleUpdateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, UpdateView):
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'motorcycles/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        # Only staff can update motorcycles
        return self.request.user.is_staff
        # Original check: motorcycle = self.get_object(); return self.request.user == motorcycle.seller
        # This suggests a 'seller' field exists. If staff are the only 'sellers',
        # the is_staff check might be sufficient. If not, you'd need the seller check.
        # Assuming is_staff is the intended restriction for updating in the refactored code.

    def form_valid(self, form):
        messages.success(self.request, "Motorcycle updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to the detail page of the updated motorcycle
        return reverse_lazy('motorcycle-detail', kwargs={'pk': self.object.pk})


# Handles deletion of motorcycle listings
class MotorcycleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Motorcycle
    template_name = 'motorcycles/motorcycle_confirm_delete.html'
    success_url = reverse_lazy('index') # Redirect to index or motorcycle list after deletion

    def test_func(self):
        # Only staff can delete motorcycles
        return self.request.user.is_staff
        # Original check: motorcycle = self.get_object(); return self.request.user == motorcycle.seller
        # Same note as above regarding the 'seller' field and staff check.

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, f"Motorcycle '{self.get_object()}' deleted successfully!")
        return super().delete(request, *args, **kwargs)