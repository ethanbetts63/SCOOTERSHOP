from django.views.generic import CreateView, UpdateView # Keep both imported for clarity, but use UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from inventory.models import Motorcycle, MotorcycleCondition, MotorcycleImage
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from inventory.forms.admin_motorcycle_image_form import MotorcycleImageFormSet
from inventory.mixins import AdminRequiredMixin


# --- THE FIX IS HERE: Changed CreateView to UpdateView ---
class MotorcycleCreateUpdateView(AdminRequiredMixin, UpdateView):
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/admin_motorcycle_create_update.html'
    context_object_name = 'motorcycle'

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.
        For updates, it fetches by 'pk'. For creates, it returns None.
        UpdateView will call this automatically when a PK is present.
        """
        pk = self.kwargs.get('pk')
        # print(f"DEBUG: MotorcycleCreateUpdateView - get_object called. PK from kwargs: {pk}") # Debug print
        if pk:
            try:
                obj = get_object_or_404(Motorcycle, pk=pk)
                # print(f"DEBUG: MotorcycleCreateUpdateView - Object found: {obj.title} (PK: {obj.pk})") # Debug print
                return obj
            except Exception as e:
                # print(f"ERROR: MotorcycleCreateUpdateView - Failed to get object for PK {pk}: {e}") # Debug print
                raise # Re-raise to ensure Django's 404 handling or error page
        # print("DEBUG: MotorcycleCreateUpdateView - No PK in kwargs, returning None (create view).") # Debug print
        return None

    def get_context_data(self, **kwargs):
        """
        Insert the formset for existing images into the context.
        """
        context = super().get_context_data(**kwargs)

        # Ensure required conditions exist in the database
        required_conditions = ['new', 'used', 'demo', 'hire']
        for condition_name in required_conditions:
            MotorcycleCondition.objects.get_or_create(
                name=condition_name,
                defaults={'display_name': condition_name.capitalize()}
            )

        # self.object is now reliably set by UpdateView's dispatch/get methods
        # based on get_object() being called when a PK is in the URL.
        # print(f"DEBUG: MotorcycleCreateUpdateView - get_context_data called. self.object: {self.object}") # Debug print

        if self.request.POST:
            # print("DEBUG: MotorcycleCreateUpdateView - Initializing image_formset with POST data.") # Debug print
            context['image_formset'] = MotorcycleImageFormSet(self.request.POST, instance=self.object)
        else:
            # print("DEBUG: MotorcycleCreateUpdateView - Initializing image_formset for GET request (instance will pre-fill).") # Debug print
            context['image_formset'] = MotorcycleImageFormSet(instance=self.object)

        if self.object:
            context['title'] = f'Edit Motorcycle: {self.object.title}'
        else:
            context['title'] = 'Add New Motorcycle'
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, validating the form and formset,
        and processing both single and multiple file uploads.
        """
        self.object = self.get_object() # This ensures self.object is set if it's an update
        form = self.get_form() # get_form() will now correctly pass self.object as instance
        
        # print(f"DEBUG: MotorcycleCreateUpdateView - POST method called. self.object: {self.object}") # Debug print
        # print(f"DEBUG: MotorcycleCreateUpdateView - Form instance during POST: {form.instance}") # Debug print

        image_formset = MotorcycleImageFormSet(self.request.POST, instance=self.object)

        if form.is_valid() and image_formset.is_valid():
            # print("DEBUG: MotorcycleCreateUpdateView - Form and formset are valid. Saving.") # Debug print
            self.object = form.save()
            image_formset.save()

            for image_file in request.FILES.getlist('additional_images'):
                MotorcycleImage.objects.create(motorcycle=self.object, image=image_file)

            messages.success(self.request, "Motorcycle saved successfully!")
            return redirect(self.get_success_url())
        else:
            # print(f"DEBUG: MotorcycleCreateUpdateView - Form errors: {form.errors}") # Debug print
            # print(f"DEBUG: MotorcycleCreateUpdateView - Image Formset errors: {image_formset.errors}") # Debug print
            messages.error(self.request, "Please correct the errors below.")
            return self.render_to_response(self.get_context_data(form=form, image_formset=image_formset))

    def get_success_url(self):
        """
        Return the URL to redirect to after successful processing.
        Redirect to the detail page of the created/updated motorcycle.
        """
        if self.object:
            return reverse_lazy('inventory:admin_motorcycle_details', kwargs={'pk': self.object.pk})
        return reverse_lazy('inventory:admin_inventory_management')

