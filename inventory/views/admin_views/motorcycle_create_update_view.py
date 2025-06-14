from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from inventory.models import Motorcycle, MotorcycleCondition, MotorcycleImage
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from inventory.forms.admin_motorcycle_image_form import MotorcycleImageFormSet
from inventory.mixins import AdminRequiredMixin


class MotorcycleCreateUpdateView(AdminRequiredMixin, CreateView):
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/admin_motorcycle_create_update.html'
    context_object_name = 'motorcycle'

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.
        For updates, it fetches by 'pk'. For creates, it returns None.
        """
        if self.kwargs.get('pk'):
            return get_object_or_404(Motorcycle, pk=self.kwargs['pk'])
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

        # When re-rendering the form due to an error, use the submitted data.
        # Otherwise, for a GET request, initialize a fresh formset.
        if self.request.POST:
            context['image_formset'] = MotorcycleImageFormSet(self.request.POST, instance=self.object)
        else:
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
        self.object = self.get_object()
        form = self.get_form()
        
        # The formset handles deletions of existing images.
        # We don't pass request.FILES here because new uploads are handled separately.
        image_formset = MotorcycleImageFormSet(self.request.POST, instance=self.object)

        if form.is_valid() and image_formset.is_valid():
            # Save the main Motorcycle instance
            self.object = form.save()

            # Save the formset to process deletions of existing images
            image_formset.save()

            # Process the newly uploaded additional images
            for image_file in request.FILES.getlist('additional_images'):
                MotorcycleImage.objects.create(motorcycle=self.object, image=image_file)

            messages.success(self.request, "Motorcycle saved successfully!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Please correct the errors below.")
            # If form or formset is invalid, re-render the page with errors
            return self.render_to_response(self.get_context_data(form=form, image_formset=image_formset))

    def get_success_url(self):
        """
        Return the URL to redirect to after successful processing.
        Redirect to the detail page of the created/updated motorcycle.
        """
        if self.object:
            return reverse_lazy('inventory:admin_motorcycle_details', kwargs={'pk': self.object.pk})
        # Fallback if object not created for some reason
        return reverse_lazy('inventory:admin_inventory_management')
