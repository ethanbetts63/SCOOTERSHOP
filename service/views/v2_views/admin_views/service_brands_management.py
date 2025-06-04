# SCOOTER_SHOP/service/views/service_brands_management.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction

from service.models import ServiceBrand # Assuming ServiceBrand model exists
from service.forms import ServiceBrandForm # Assuming ServiceBrandForm exists
# Removed ServiceSettings import as max_primary_brands is no longer used

class ServiceBrandManagementView(View):
    """
    Class-based view for managing (listing, adding, and editing) service brands.
    Handles GET (display form and list) and POST (add/edit brand).
    """
    template_name = 'service/service_brands_management.html'
    form_class = ServiceBrandForm

    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def get_context_data(self, form=None, edit_brand=None):
        """Helper method to get context data for rendering the template."""
        # Order service brands alphabetically by name
        service_brands = ServiceBrand.objects.all().order_by('name')

        # Removed primary_brands_count and max_primary_brands as they are no longer needed

        if form is None:
            form = self.form_class(instance=edit_brand)

        context = {
            'form': form,
            'edit_brand': edit_brand,
            'service_brands': service_brands,
            'page_title': 'Manage Service Brands',
        }
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: displays the form for adding/editing brands
        and lists all existing service brands.
        """
        edit_brand_pk = request.GET.get('edit_brand_pk')
        edit_brand = None
        if edit_brand_pk:
            edit_brand = get_object_or_404(ServiceBrand, pk=edit_brand_pk)

        context = self.get_context_data(edit_brand=edit_brand)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests: processes form submissions for adding,
        editing, or deleting a service brand.
        """
        form = None
        edit_brand = None

        if 'add_brand_submit' in request.POST:
            brand_id = request.POST.get('brand_id') # Hidden input for editing existing brand
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
                    messages.success(self.request, f"Service brand '{brand.name}' {action} successfully.")
                    return redirect('service:service_brands_management')
                except ValueError as e:
                    messages.error(self.request, str(e))
                except Exception as e:
                    messages.error(self.request, f"Error saving service brand: {e}")
            else:
                messages.error(self.request, "Please correct the errors below.")

        # If form is invalid or another action was attempted (e.g., direct edit click)
        # re-render the page with appropriate context
        context = self.get_context_data(form=form, edit_brand=edit_brand)
        return render(request, self.template_name, context)
