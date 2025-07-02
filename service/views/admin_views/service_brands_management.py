from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction

from service.models import ServiceBrand
from service.forms import ServiceBrandForm


class ServiceBrandManagementView(View):

    template_name = "service/service_brands_management.html"
    form_class = ServiceBrandForm

    def get_context_data(self, form=None, edit_brand=None):

        service_brands = ServiceBrand.objects.all().order_by("name")

        if form is None:
            form = self.form_class(instance=edit_brand)

        context = {
            "form": form,
            "edit_brand": edit_brand,
            "service_brands": service_brands,
            "page_title": "Manage Service Brands",
        }
        return context

    def get(self, request, *args, **kwargs):

        edit_brand_pk = request.GET.get("edit_brand_pk")
        edit_brand = None
        if edit_brand_pk:
            edit_brand = get_object_or_404(ServiceBrand, pk=edit_brand_pk)

        context = self.get_context_data(edit_brand=edit_brand)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        form = None
        edit_brand = None

        if "add_brand_submit" in request.POST:
            brand_id = request.POST.get("brand_id")
            if brand_id:
                edit_brand = get_object_or_404(ServiceBrand, pk=brand_id)
                form = self.form_class(request.POST, request.FILES, instance=edit_brand)
            else:
                form = self.form_class(request.POST, request.FILES)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        brand = form.save()

                    action = "updated" if brand_id else "added"
                    messages.success(
                        self.request,
                        f"Service brand '{brand.name}' {action} successfully.",
                    )
                    return redirect("service:service_brands_management")
                except ValueError as e:
                    messages.error(self.request, str(e))
                except Exception as e:
                    messages.error(self.request, f"Error saving service brand: {e}")
            else:
                messages.error(self.request, "Please correct the errors below.")

        context = self.get_context_data(form=form, edit_brand=edit_brand)
        return render(request, self.template_name, context)
