# inventory/views/motorcycle_detail.py

from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.conf import settings

from inventory.models import Motorcycle, MotorcycleImage, MotorcycleCondition
from inventory.forms import MotorcycleForm, MotorcycleImageFormSet
# Assuming .utils exists and has get_featured_motorcycles
# from .utils import get_featured_motorcycles

# Mock get_featured_motorcycles if .utils is not available in this environment
# If you have a .utils file, remove this mock function
def get_featured_motorcycles(exclude_id, limit, condition):
    """
    Mock function for get_featured_motorcycles.
    Replace with actual import if .utils is available.
    """
    # print(f"Mock get_featured_motorcycles called with exclude_id={exclude_id}, limit={limit}, condition={condition}")
    return []


class MotorcycleDetailView(DetailView):
    """Displays detailed information about a specific motorcycle."""
    model = Motorcycle
    template_name = 'inventory/motorcycle_detail.html'
    context_object_name = 'motorcycle'

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

        # Determine if the motorcycle has the 'hire' or 'new' condition for filtering specs
        is_for_hire = self.object.conditions.filter(name='hire').exists()
        is_new = self.object.conditions.filter(name='new').exists()
        is_for_sale = self.object.conditions.filter(name__in=['new', 'used', 'demo']).exists() # Check if any sale condition is present

        # Define specifications with their labels and icons
        motorcycle = self.object
        specifications = []

        # Always include condition if available
        if motorcycle.conditions.exists():
             specifications.append({'field': 'condition', 'label': 'Condition', 'icon': 'icon-category', 'value': motorcycle.get_conditions_display()})

        # Conditionally add other specifications
        if motorcycle.year is not None: specifications.append({'field': 'year', 'label': 'Year', 'icon': 'icon-year', 'value': motorcycle.year})
        # Odometer is now always required, so include it if its value exists (should always exist if required)
        if motorcycle.odometer is not None: specifications.append({'field': 'odometer', 'label': 'Odometer', 'icon': 'icon-odometer', 'value': f"{motorcycle.odometer} km"})
        if motorcycle.engine_size: specifications.append({'field': 'engine_size', 'label': 'Engine', 'icon': 'icon-capacity', 'value': f"{motorcycle.engine_size}cc"}) # Assuming engine_size remains required/always has a value
        if motorcycle.seats is not None: specifications.append({'field': 'seats', 'label': 'Seats', 'icon': 'icon-seat', 'value': motorcycle.seats})
        if motorcycle.transmission: specifications.append({'field': 'transmission', 'label': 'Transmission', 'icon': 'icon-transmission', 'value': motorcycle.transmission})
        # Include Rego/Rego Expiry if not New
        if motorcycle.rego and not is_new: specifications.append({'field': 'rego', 'label': 'Registration', 'icon': 'icon-rego', 'value': motorcycle.rego})
        if motorcycle.rego_exp and not is_new: specifications.append({'field': 'rego_exp', 'label': 'Rego Expires', 'icon': 'icon-rego-exp', 'value': motorcycle.rego_exp.strftime("%d %b %Y")})
        # Include Stock Number if New, Used, or Demo
        if motorcycle.stock_number and is_for_sale: specifications.append({'field': 'stock_number', 'label': 'Stock #', 'icon': 'icon-stock', 'value': motorcycle.stock_number})

        # Handle price display logic - always add the price field if any sale condition is present
        if is_for_sale:
            price_value = f"${motorcycle.price:.2f}" if motorcycle.price is not None else "Contact for price"
            specifications.append({'field': 'price', 'label': 'Price', 'icon': 'icon-money', 'value': price_value})

        # Handle hire rate display logic - always add the daily hire rate if hire condition is present
        if is_for_hire:
            # Assuming you have a settings.DEFAULT_DAILY_HIRE_RATE
            default_daily_rate = getattr(settings, 'DEFAULT_DAILY_HIRE_RATE', None)
            daily_rate_value = f"${motorcycle.daily_hire_rate:.2f}" if motorcycle.daily_hire_rate is not None else (f"Default ({default_daily_rate:.2f})" if default_daily_rate is not None else "Contact for rate")
            specifications.append({'field': 'daily_hire_rate', 'label': 'Daily Hire Rate', 'icon': 'icon-money', 'value': daily_rate_value})
             # Add other hire rates if they exist
            if motorcycle.hourly_hire_rate is not None:
                 specifications.append({'field': 'hourly_hire_rate', 'label': 'Hourly Rate', 'icon': 'icon-money', 'value': f"${motorcycle.hourly_hire_rate:.2f}"})
            if motorcycle.weekly_hire_rate is not None:
                 specifications.append({'field': 'weekly_hire_rate', 'label': 'Weekly Rate', 'icon': 'icon-money', 'value': f"${motorcycle.weekly_hire_rate:.2f}"})
            if motorcycle.monthly_hire_rate is not None:
                 specifications.append({'field': 'monthly_hire_rate', 'label': 'Monthly Rate', 'icon': 'icon-money', 'value': f"${motorcycle.monthly_hire_rate:.2f}"})

        context['filtered_specifications'] = specifications

        return context


class MotorcycleFormHandlerMixin:
    """Mixin to handle saving the main form and the image formset."""
    def form_valid(self, form):
        """
        Handles the valid main form and validates/saves the image formset.
        """
        context = self.get_context_data()
        images_formset = context['images_formset']

        # Ensure the formset is bound to the form instance before validation
        # This is crucial for inline formsets, especially in update views
        if self.object: # Check if we have an instance (UpdateView)
             images_formset.instance = self.object

        # --- MODIFIED: Check if the formset is valid BEFORE saving anything ---
        # If the formset is not valid, we stop here and render the form with errors.
        if images_formset.is_valid():
            # Both main form and formset are valid. Proceed with saving.

            # Save the main form first to get the instance (required for formset)
            self.object = form.save()

            # Handle multiple uploaded files from the 'additional_images' input
            # This input is separate from the formset and handles new uploads
            additional_images = self.request.FILES.getlist('additional_images')
            for image_file in additional_images:
                if image_file: # Ensure there's actually a file
                    try:
                        MotorcycleImage.objects.create(
                            motorcycle=self.object,
                            image=image_file
                        )
                    except Exception as e:
                        # Log or add a message if a file upload fails
                        messages.error(self.request, f"Failed to upload image {image_file.name}: {e}")
                        print(f"Error uploading image {image_file.name}: {e}")


            # Process the formset for existing images (for deletions and changes)
            # Link the formset to the saved motorcycle instance
            images_formset.instance = self.object
            # Save the formset - this handles deletions and changes to existing images
            try:
                images_formset.save()
            except Exception as e:
                 # Catch potential errors during formset save
                 messages.error(self.request, f"Error saving image changes: {e}")
                 print(f"Error saving image formset: {e}")
                 # You might want to redirect or re-render here depending on desired behavior
                 # For now, we'll let the main form's success_url handle redirection,
                 # but the error message will be displayed.

            # Proceed with the default form_valid behavior (redirect to success_url)
            return super().form_valid(form)
        else:
            # --- MODIFIED: If the formset is NOT valid, render the form with errors ---
            # This prevents the AttributeError by not attempting to save an invalid formset.
            # The formset errors will be available in the context and displayed in the template.
            print(f"Image formset is invalid: {images_formset.errors}") # Log formset errors
            # Add formset errors to messages for user feedback
            # Iterate through formset errors (errors is a list of dicts, one dict per form)
            for i, formset_form_errors in enumerate(images_formset.errors):
                 if formset_form_errors: # Check if the form has errors
                     messages.error(self.request, f"Error in Image Form #{i+1}:")
                     for field, errors in formset_form_errors.items():
                          for error in errors:
                               messages.error(self.request, f"- {field}: {error}")

            # Add non-field errors for the formset itself
            for error in images_formset.non_form_errors():
                 messages.error(self.request, f"Image formset error: {error}")

            # Render the template with the valid main form and the invalid formset
            context['form'] = form # Ensure the valid main form is in context
            # The formset is already in context from get_context_data
            return render(self.request, self.template_name, context)


    def form_invalid(self, form):
        """
        Handles the invalid main form.
        """
        # Include formset in context when the main form is invalid
        context = self.get_context_data()
        context['form'] = form # Ensure the invalid main form is in context
        # The formset is already added in get_context_data if request is POST

        # Add formset errors to messages if any (already handled in form_valid, but good to be safe)
        if 'images_formset' in context and context['images_formset'].errors:
             for i, formset_form_errors in enumerate(context['images_formset'].errors):
                 if formset_form_errors:
                     messages.error(self.request, f"Error in Image Form #{i+1}:")
                     for field, errors in formset_form_errors.items():
                          for error in errors:
                               messages.error(self.request, f"- {field}: {error}")
             for error in context['images_formset'].non_form_errors():
                  messages.error(self.request, f"Image formset error: {error}")


        # Render the template with the invalid main form and the formset
        return render(self.request, self.template_name, context)


    def get_context_data(self, **kwargs):
        """
        Adds the image formset to the context.
        """
        context = super().get_context_data(**kwargs)
        # Pass the instance to the formset for UpdateView
        instance = self.object if hasattr(self, 'object') else None

        if self.request.method == 'POST':
            # If POST, populate formset with data and files
            context['images_formset'] = MotorcycleImageFormSet(self.request.POST, self.request.FILES, instance=instance)
        else:
            # If GET, populate formset with existing images if instance exists
            context['images_formset'] = MotorcycleImageFormSet(instance=instance)

        return context


class MotorcycleCreateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, CreateView):
    """View for creating a new motorcycle listing."""
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        """Only staff can create motorcycles."""
        return self.request.user.is_staff

    def dispatch(self, request, *args, **kwargs):
        """Ensure base conditions exist before handling the request."""
        conditions_to_create = [
            ('new', 'New'),
            ('used', 'Used'),
            ('demo', 'Demo'),
            ('hire', 'Hire'),
        ]
        for name, display_name in conditions_to_create:
            MotorcycleCondition.objects.get_or_create(
                name=name,
                defaults={'display_name': display_name}
            )
        # Call the parent dispatch method to continue the request flow
        return super().dispatch(request, *args, **kwargs)

    # form_valid is handled by the mixin now, but we can override to add messages
    def form_valid(self, form):
        """Handle form valid and add success message."""
        # The form_valid logic is now largely handled by the mixin.
        # Call the mixin's form_valid which will save and redirect if formset is also valid.
        response = super().form_valid(form)
        # The success message is added within the mixin's form_valid before the super call
        return response


    def get_success_url(self):
        """Redirect to the detail page of the newly created motorcycle."""
        # This will only be called if form_valid (and thus formset validation) succeeded
        return reverse_lazy('inventory:motorcycle-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create_view'] = True
        context['page_title'] = 'Add New Motorcycle'
        return context


class MotorcycleUpdateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, UpdateView):
    """View for updating an existing motorcycle listing."""
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        """Only staff can update motorcycles."""
        # Assuming staff are the only ones who manage inventory, the is_staff check is sufficient.
        return self.request.user.is_staff

    # form_valid is handled by the mixin now, but we can override to add messages
    def form_valid(self, form):
        """Handle form valid and add success message."""
        # The form_valid logic is now largely handled by the mixin.
        # Call the mixin's form_valid which will save and redirect if formset is also valid.
        response = super().form_valid(form)
        # The success message is added within the mixin's form_valid before the super call
        return response


    def get_success_url(self):
        """Redirect to the detail page of the updated motorcycle."""
        # This will only be called if form_valid (and thus formset validation) succeeded
        return reverse_lazy('inventory:motorcycle-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update_view'] = True
        context['page_title'] = f'Edit {self.object.year} {self.object.brand} {self.object.model}'
        return context


# Handles deletion of motorcycle listings
class MotorcycleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View for deleting a motorcycle listing."""
    model = Motorcycle
    template_name = 'inventory/motorcycles/motorcycle_confirm_delete.html'
    success_url = reverse_lazy('core:index') # Redirect to index or motorcycle list after deletion

    def test_func(self):
        """Only staff can delete motorcycles."""
        # Assuming staff are the only ones who manage inventory, the is_staff check is sufficient.
        return self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, f"Motorcycle '{self.get_object()}' deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Delete Motorcycle'
        return context

