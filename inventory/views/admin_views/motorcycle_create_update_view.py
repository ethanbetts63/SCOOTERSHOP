from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404
from inventory.models import Motorcycle
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from inventory.forms.admin_motorcycle_image_form import MotorcycleImageFormSet


class MotorcycleCreateUpdateView(CreateView, UpdateView):
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/admin_motorcycle_create_update.html'
    context_object_name = 'motorcycle'

    def get_object(self, queryset=None):
        if self.kwargs.get('pk'):
            return get_object_or_404(Motorcycle, pk=self.kwargs['pk'])
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            context['title'] = f'Edit Motorcycle: {self.object.title}'
            context['image_formset'] = MotorcycleImageFormSet(instance=self.object)
        else:
            context['title'] = 'Add New Motorcycle'
            context['image_formset'] = MotorcycleImageFormSet()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        image_formset = MotorcycleImageFormSet(self.request.POST, self.request.FILES, instance=self.object)

        if form.is_valid() and image_formset.is_valid():
            return self.form_valid(form, image_formset)
        else:
            return self.form_invalid(form, image_formset)

    def form_valid(self, form, image_formset):
        self.object = form.save()
        image_formset.instance = self.object
        image_formset.save()
        messages.success(self.request, "Motorcycle saved successfully!")
        return super().form_valid(form)

    def form_invalid(self, form, image_formset):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form, image_formset=image_formset))

    def get_success_url(self):
        return reverse_lazy('inventory:admin_motorcycle_details', kwargs={'pk': self.object.pk})

