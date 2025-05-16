# SCOOTER_SHOP/dashboard/views/dashboard.py

# Keep necessary imports for the remaining views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.db import transaction
from dashboard.models import SiteSettings, AboutPageContent, BlockedServiceDate, ServiceBrand
from service.models import ServiceType 
from dashboard.models import HireSettings

from dashboard.forms import (
    BusinessInfoForm,
    HireBookingSettingsForm,
    ServiceBookingSettingsForm,
    VisibilitySettingsForm,
    ServiceTypeForm,
    AboutPageContentForm,
    BlockedServiceDateForm,
    ServiceBrandForm
)

@user_passes_test(lambda u: u.is_staff)
def dashboard_index(request):
    context = {
        'page_title': 'Admin Dashboard',
        # Add any data you want to display on the admin index here
    }
    # Updated template path
    return render(request, 'dashboard/dashboard_index.html', context)

# --- Existing Settings Views (Keep these) ---
@user_passes_test(lambda u: u.is_staff)
def settings_business_info(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = BusinessInfoForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business information updated successfully!')
            return redirect('dashboard:settings_business_info')
    else:
        form = BusinessInfoForm(instance=settings)
    context = {
        'page_title': 'Business Information Settings',
        'form': form,
        'active_tab': 'business_info'
    }
    return render(request, 'dashboard/settings_business_info.html', context)


@user_passes_test(lambda u: u.is_staff)
def settings_hire_booking(request):
    # Use get_or_create to ensure the HireSettings object exists.
    # If it doesn't exist, it will be created with default values.
    settings, created = HireSettings.objects.get_or_create()

    if created:
        # Optional: Add a message the first time it's created
        messages.info(request, "Initial Hire Settings object created with default values.")

    if request.method == 'POST':
        form = HireBookingSettingsForm(request.POST, instance=settings)
        # Your print statement to confirm form validity
        print("Is form valid?", form.is_valid())
        if form.is_valid():
            form.save()
            messages.success(request, 'Hire booking settings updated successfully!')
            return redirect('dashboard:settings_hire_booking') # Redirect after successful save
        else:
            # Add a message if the form is not valid (though your print showed it was valid)
            messages.error(request, 'Please correct the errors below.')
    else:
        # For GET requests, the form is initialized with the retrieved or created settings object
        form = HireBookingSettingsForm(instance=settings)

    context = {
        'page_title': 'Hire Booking Settings',
        'form': form,
        'active_tab': 'hire_booking'
    }
    return render(request, 'dashboard/settings_hire_booking.html', context)

@user_passes_test(lambda u: u.is_staff)
def settings_service_booking(request):
    settings = SiteSettings.get_settings()
    blocked_service_dates = BlockedServiceDate.objects.all() # Get all blocked dates

    # Initialize forms outside of POST to have them available for GET or failed POST
    form = ServiceBookingSettingsForm(instance=settings)
    blocked_service_date_form = BlockedServiceDateForm()

    if request.method == 'POST':
        # Handle ServiceBookingSettingsForm submission
        if 'service_settings_submit' in request.POST:
            form = ServiceBookingSettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                messages.success(request, 'Service booking settings updated successfully!')
                return redirect('dashboard:settings_service_booking') # Redirect on success
            else:
                messages.error(request, 'Error updating service booking settings. Please check the form.')
        # Handle BlockedServiceDateForm submission
        elif 'add_blocked_service_date_submit' in request.POST:
            blocked_service_date_form = BlockedServiceDateForm(request.POST)
            if blocked_service_date_form.is_valid():
                blocked_service_date_form.save()
                messages.success(request, 'Blocked date added successfully!')
                return redirect('dashboard:settings_service_booking') # Redirect on success
            else:
                 messages.error(request, 'Error adding blocked date. Please check the form.')
        # Handle Delete Blocked Date
        elif 'delete_blocked_service_date' in request.POST:
            blocked_service_date_id = request.POST.get('delete_blocked_service_date')
            try:
                blocked_service_date = get_object_or_404(BlockedServiceDate, pk=blocked_service_date_id)
                blocked_service_date.delete()
                messages.success(request, 'Blocked date deleted successfully!')
                return redirect('dashboard:settings_service_booking') # Redirect on success
            except Exception as e:
                 messages.error(request, f'Error deleting blocked date: {e}')
                 return redirect('dashboard:settings_service_booking') # Redirect even on error

        # If none of the specific submit buttons were pressed, maybe handle a general POST error
        # This part might need refinement depending on how you structure your form submissions
        # If you have multiple forms submitting to the same view, checking the submit button name is good.

    # Context for GET requests or failed POST requests
    context = {
        'page_title': 'Service Booking Settings',
        'form': form, # Service booking settings form
        'blocked_service_date_form': blocked_service_date_form, # Form for adding blocked dates
        'blocked_service_dates': blocked_service_dates, # List of existing blocked dates
        'active_tab': 'service_booking'
    }
    return render(request, 'dashboard/settings_service_booking.html', context)


@user_passes_test(lambda u: u.is_staff)
def settings_service_types(request):
    # Get all service types - Requires ServiceType model import
    service_types = ServiceType.objects.all().order_by('name')
    context = {
        'page_title': 'Service Types Management',
        'service_types': service_types,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/settings_service_types.html', context)


@user_passes_test(lambda u: u.is_staff)
def delete_service_type(request, pk):
    # Requires get_object_or_404, ServiceType, messages imports
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        name = service_type.name
        service_type.delete()
        messages.success(request, f"Service type '{name}' deleted successfully!")
        return redirect('dashboard:settings_service_types')
    context = {
        'page_title': 'Delete Service Type',
        'service_type': service_type
    }
    return render(request, 'dashboard/delete_service_type.html', context)


@user_passes_test(lambda u: u.is_staff)
def edit_service_type(request, pk):
    # Requires get_object_or_404, ServiceType, ServiceTypeForm, messages imports
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES, instance=service_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service type '{service_type.name}' updated successfully!")
            return redirect('dashboard:settings_service_types')
    else:
        form = ServiceTypeForm(instance=service_type)
    context = {
        'page_title': 'Edit Service Type',
        'form': form,
        'service_type': service_type,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/add_edit_service_type.html', context)


@user_passes_test(lambda u: u.is_staff)
def add_service_type(request):
    # Requires ServiceTypeForm, messages imports
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES)
        if form.is_valid():
            service_type = form.save(commit=False)
            # Ensure estimated_duration is handled if your form logic requires it here
            # Assign the calculated estimated_duration from the form's cleaned_data
            service_type.estimated_duration = form.cleaned_data['estimated_duration'] # Add this line
            service_type.save()
            messages.success(request, f"Service type '{service_type.name}' added successfully!")
            return redirect('dashboard:settings_service_types')
    else:
        form = ServiceTypeForm()
    context = {
        'page_title': 'Add New Service Type',
        'form': form,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/add_edit_service_type.html', context)


@user_passes_test(lambda u: u.is_staff)
def settings_visibility(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = VisibilitySettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Visibility settings updated successfully!')
            return redirect('dashboard:settings_visibility')
    else:
        form = VisibilitySettingsForm(instance=settings)
    context = {
        'page_title': 'Visibility Settings',
        'form': form,
        'active_tab': 'visibility'
    }
    return render(request, 'dashboard/settings_visibility.html', context)

@user_passes_test(lambda u: u.is_staff)
def edit_about_page(request):
    about_content, created = AboutPageContent.objects.get_or_create()
    if request.method == 'POST':
        form = AboutPageContentForm(request.POST, request.FILES, instance=about_content)
        if form.is_valid():
            form.save()
            messages.success(request, "About page content updated successfully!")
            return redirect('core:about') # Assuming 'core:about' exists
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AboutPageContentForm(instance=about_content)
    context = {
        'page_title': 'Edit About Page',
        'form': form,
        'about_content': about_content,
        'active_tab': 'about_page'
    }
    return render(request, 'dashboard/edit_about_page.html', context)

    # Add import at the top:
from django.http import JsonResponse

@user_passes_test(lambda u: u.is_staff)
def toggle_service_type_active_status(request, pk):
    # Ensure only POST requests are accepted
    if request.method == 'POST':
        service_type = get_object_or_404(ServiceType, pk=pk)
        # Toggle the is_active status
        service_type.is_active = not service_type.is_active
        service_type.save()

        status_text = "activated" if service_type.is_active else "deactivated"
        messages.success(request, f"Service type '{service_type.name}' has been {status_text}.")

        # Return a success response (AJAX)
        return JsonResponse({'status': 'success', 'is_active': service_type.is_active, 'message': f"Service type '{service_type.name}' has been {status_text}."})
    else:
        # Return Method Not Allowed for non-POST requests
        return JsonResponse({'error': 'Invalid request method'}, status=405)


@user_passes_test(lambda u: u.is_staff)
def service_brands_management(request):
    """
    Dashboard view for managing service brands.
    Handles adding new brands and editing existing ones.
    """
    service_brands = ServiceBrand.objects.all().order_by('-is_primary', 'name')  # Order primary first, then by name
    primary_brands_count = ServiceBrand.objects.filter(is_primary=True).count()
    
    # Initialize form variables
    form = None
    edit_brand = None
    
    # Handle POST requests (Add, Edit, or Delete)
    if request.method == 'POST':
        # Handle Add/Edit Brand Form Submission
        if 'add_brand_submit' in request.POST:
            # Check if we're editing an existing brand
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
                    # Catch the specific error raised by our model's save method
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f"Error saving service brand: {e}")
            else:
                # Form is not valid, errors are attached to the form
                messages.error(request, "Please correct the errors below.")

        # Handle Delete Brand Request
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
        
        # Handle Edit Request (GET form for editing)
        elif 'edit_brand_pk' in request.POST:
            brand_pk = request.POST.get('edit_brand_pk')
            edit_brand = get_object_or_404(ServiceBrand, pk=brand_pk)
            form = ServiceBrandForm(instance=edit_brand)
        
        else:
            # Unexpected POST request
            messages.error(request, "Invalid request.")
    
    # Handle GET request or form preparation after POST
    if form is None:  # Only create a new form if not already set
        form = ServiceBrandForm(instance=edit_brand)  # Empty form or populated for editing
    
    # Prepare context for rendering
    context = {
        'form': form,
        'edit_brand': edit_brand,  # Pass the brand being edited (if any)
        'service_brands': service_brands,
        'primary_brands_count': primary_brands_count,
        'max_primary_brands': 5,
        'page_title': 'Manage Service Brands',
    }
    
    return render(request, 'dashboard/service_brands_management.html', context)


@user_passes_test(lambda u: u.is_staff)
def delete_service_brand(request, pk):
    """
    View to handle deleting a service brand via POST request.
    Separate view for cleaner URL routing.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method. Please use the form to delete brands.")
        return redirect('dashboard:service_brands_management')
    
    try:
        brand_to_delete = get_object_or_404(ServiceBrand, pk=pk)
        brand_name = brand_to_delete.name
        brand_to_delete.delete()
        messages.success(request, f"Service brand '{brand_name}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting service brand: {e}")
    
    return redirect('dashboard:service_brands_management')