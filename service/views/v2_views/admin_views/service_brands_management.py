# SCOOTER_SHOP/dashboard/views/service_brands_management.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction

from service.models import ServiceBrand
from service.forms import ServiceBrandForm

@user_passes_test(lambda u: u.is_staff)
def service_brands_management(request):
    service_brands = ServiceBrand.objects.all().order_by('-is_primary', 'name')
    primary_brands_count = ServiceBrand.objects.filter(is_primary=True).count()

    form = None
    edit_brand = None

    if request.method == 'POST':
        if 'add_brand_submit' in request.POST:
            brand_id = request.POST.get('brand_id')
            if brand_id:
                edit_brand = get_object_or_404(ServiceBrand, pk=brand_id)
                form = ServiceBrandForm(request.POST, request.FILES, instance=edit_brand)
            else:
                form = ServiceBrandForm(request.POST, request.FILES)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        brand = form.save()

                    action = "updated" if brand_id else "added"
                    messages.success(request, f"Service brand '{brand.name}' {action} successfully.")
                    return redirect('dashboard:service_brands_management')
                except ValueError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f"Error saving service brand: {e}")
            else:
                messages.error(request, "Please correct the errors below.")

        elif 'delete_brand_pk' in request.POST:
            brand_pk = request.POST.get('delete_brand_pk')
            try:
                brand_to_delete = get_object_or_404(ServiceBrand, pk=brand_pk)
                brand_name = brand_to_delete.name
                brand_to_delete.delete()
                messages.success(request, f"Service brand '{brand_name}' deleted successfully.")
            except Exception as e:
                messages.error(request, f"Error deleting service brand: {e}")
            return redirect('dashboard:service_brands_management')

        elif 'edit_brand_pk' in request.POST:
            brand_pk = request.POST.get('edit_brand_pk')
            edit_brand = get_object_or_404(ServiceBrand, pk=brand_pk)
            form = ServiceBrandForm(instance=edit_brand)

        else:
            messages.error(request, "Invalid request.")

    if form is None:
        form = ServiceBrandForm(instance=edit_brand)

    context = {
        'form': form,
        'edit_brand': edit_brand,
        'service_brands': service_brands,
        'primary_brands_count': primary_brands_count,
        'max_primary_brands': 5,
        'page_title': 'Manage Service Brands',
    }

    return render(request, 'dashboard/service_brands_management.html', context)