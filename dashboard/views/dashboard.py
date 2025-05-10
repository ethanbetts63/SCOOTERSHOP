# SCOOTER_SHOP/dashboard/views/dashboard.py

# Keep necessary imports for the remaining views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse

# Import models from the dashboard app
# Import BlockedDate model
from dashboard.models import SiteSettings, AboutPageContent, BlockedDate, ServiceBrand
from service.models import ServiceType # <-- Re-added this import


# Import forms from the dashboard app (Keep forms needed by remaining views)
# Import BlockedDateForm
from dashboard.forms import (
    BusinessInfoForm,
    HireBookingSettingsForm,
    ServiceBookingSettingsForm,
    VisibilitySettingsForm,
    ServiceTypeForm,
    AboutPageContentForm,
    BlockedDateForm,
    ServiceBrandForm
)

# Import is_staff_check from the new bookings.py file
from .bookings import is_staff_check


@user_passes_test(is_staff_check)
def dashboard_index(request):
    context = {
        'page_title': 'Admin Dashboard',
        # Add any data you want to display on the admin index here
    }
    # Updated template path
    return render(request, 'dashboard/dashboard_index.html', context)

# --- Existing Settings Views (Keep these) ---
@user_passes_test(is_staff_check)
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


@user_passes_test(is_staff_check)
def settings_hire_booking(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = HireBookingSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hire booking settings updated successfully!')
            return redirect('dashboard:settings_hire_booking')
    else:
        form = HireBookingSettingsForm(instance=settings)
    context = {
        'page_title': 'Hire Booking Settings',
        'form': form,
        'active_tab': 'hire_booking'
    }
    return render(request, 'dashboard/settings_hire_booking.html', context)


@user_passes_test(is_staff_check)
def settings_service_booking(request):
    settings = SiteSettings.get_settings()
    blocked_dates = BlockedDate.objects.all() # Get all blocked dates

    # Initialize forms outside of POST to have them available for GET or failed POST
    form = ServiceBookingSettingsForm(instance=settings)
    blocked_date_form = BlockedDateForm()

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
        # Handle BlockedDateForm submission
        elif 'add_blocked_date_submit' in request.POST:
            blocked_date_form = BlockedDateForm(request.POST)
            if blocked_date_form.is_valid():
                blocked_date_form.save()
                messages.success(request, 'Blocked date added successfully!')
                return redirect('dashboard:settings_service_booking') # Redirect on success
            else:
                 messages.error(request, 'Error adding blocked date. Please check the form.')
        # Handle Delete Blocked Date
        elif 'delete_blocked_date' in request.POST:
            blocked_date_id = request.POST.get('delete_blocked_date')
            try:
                blocked_date = get_object_or_404(BlockedDate, pk=blocked_date_id)
                blocked_date.delete()
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
        'blocked_date_form': blocked_date_form, # Form for adding blocked dates
        'blocked_dates': blocked_dates, # List of existing blocked dates
        'active_tab': 'service_booking'
    }
    return render(request, 'dashboard/settings_service_booking.html', context)


@user_passes_test(is_staff_check)
def settings_service_types(request):
    # Get all service types - Requires ServiceType model import
    service_types = ServiceType.objects.all().order_by('name')
    context = {
        'page_title': 'Service Types Management',
        'service_types': service_types,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/settings_service_types.html', context)


@user_passes_test(is_staff_check)
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


@user_passes_test(is_staff_check)
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


@user_passes_test(is_staff_check)
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


@user_passes_test(is_staff_check)
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

@user_passes_test(is_staff_check)
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

@user_passes_test(is_staff_check)
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


@is_staff_check
def service_brands_management(request):
    """
    Dashboard view for managing service brands.
    Handles adding new brands and deleting existing ones.
    """
    service_brands = ServiceBrand.objects.all().order_by('is_primary', 'name') # Order primary first, then by name
    primary_brands_count = ServiceBrand.objects.filter(is_primary=True).count()
    max_primary_brands = 5 # Define the limit

    # Handle POST requests (Add or Delete)
    if request.method == 'POST':
        # Handle Add Brand Form Submission
        if 'add_brand_submit' in request.POST:
            form = ServiceBrandForm(request.POST, request.FILES)
            if form.is_valid():
                new_brand = form.save(commit=False) # Don't save to DB yet

                # Server-side check for the 5 primary brand limit
                if new_brand.is_primary and primary_brands_count >= max_primary_brands:
                    messages.error(request, f"Cannot add more than {max_primary_brands} primary brands.")
                    # We don't save, render the page with the form data and error
                else:
                    try:
                        new_brand.save()
                        messages.success(request, f"Service brand '{new_brand.name}' added successfully.")
                        return redirect('dashboard:settings_service_brands') # Redirect on success
                    except Exception as e: # Catch potential database errors (e.g., unique constraint)
                        messages.error(request, f"Error adding service brand: {e}")
                        # Fall through to render with form data and error

            else:
                # Form is not valid, errors are attached to the form
                messages.error(request, "Please correct the errors below.")

        # Handle Delete Brand Request
        elif 'delete_brand_pk' in request.POST:
            brand_pk = request.POST.get('delete_brand_pk')
            try:
                brand_to_delete = get_object_or_404(ServiceBrand, pk=brand_pk)
                brand_to_delete.delete()
                messages.success(request, f"Service brand '{brand_to_delete.name}' deleted successfully.")
            except Exception as e:
                 messages.error(request, f"Error deleting service brand: {e}")
            finally:
                 # Always redirect after delete POST to prevent resubmission
                 return redirect('dashboard:settings_service_brands')

        else:
            # Unexpected POST request
            messages.error(request, "Invalid request.")
            # Fall through to render the page

    else: # Handle GET request
        form = ServiceBrandForm() # Empty form for adding

    # Prepare context for rendering
    context = {
        'form': form, # Pass the form (either empty on GET or with errors on POST)
        'service_brands': service_brands, # List of all brands
        'primary_brands_count': primary_brands_count,
        'max_primary_brands': max_primary_brands,
        'page_title': 'Manage Service Brands', # Title for the template
    }

    return render(request, 'dashboard/service_brands_management.html', context)


# Add a decorator for the delete action specifically for robustness
@is_staff_check
def delete_service_brand(request, pk):
    """
    View to handle deleting a service brand via POST request.
    Separate view is cleaner for just deletion.
    """
    try:
        brand_to_delete = get_object_or_404(ServiceBrand, pk=pk)
        brand_name = brand_to_delete.name # Get name before deleting
        brand_to_delete.delete()
        messages.success(request, f"Service brand '{brand_name}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting service brand: {e}")

    # Redirect back to the management page
    return redirect('dashboard:settings_service_brands')
