from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from inventory.models import Motorcycle, MotorcycleCondition, MotorcycleImage
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from inventory.forms.admin_motorcycle_image_form import MotorcycleImageFormSet
from inventory.mixins import AdminRequiredMixin


class MotorcycleCreateUpdateView(AdminRequiredMixin, UpdateView):
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = "inventory/admin_motorcycle_create_update.html"
    context_object_name = "motorcycle"

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        if pk:
            return get_object_or_404(Motorcycle, pk=pk)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        required_conditions = ["new", "used", "demo"]
        for condition_name in required_conditions:
            MotorcycleCondition.objects.get_or_create(
                name=condition_name,
                defaults={"display_name": condition_name.capitalize()},
            )

        if self.request.POST:

            context["image_formset"] = MotorcycleImageFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context["image_formset"] = MotorcycleImageFormSet(instance=self.object)

        context["title"] = (
            f"Edit Motorcycle: {self.object.title}"
            if self.object
            else "Add New Motorcycle"
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        image_formset = MotorcycleImageFormSet(
            self.request.POST, self.request.FILES, instance=self.object
        )

        if form.is_valid() and image_formset.is_valid():
            self.object = form.save()
            image_formset.save()

            for image_file in request.FILES.getlist("additional_images"):
                MotorcycleImage.objects.create(motorcycle=self.object, image=image_file)

            messages.success(self.request, "Motorcycle saved successfully!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Please correct the errors below.")

            return self.render_to_response(
                self.get_context_data(form=form, image_formset=image_formset)
            )

    def get_success_url(self):
        if self.object:
            return reverse_lazy(
                "inventory:admin_motorcycle_details", kwargs={"pk": self.object.pk}
            )
        return reverse_lazy("inventory:admin_inventory_management")
