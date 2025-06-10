# service/utils/form_helpers.py (Updated)

from service.forms import AdminCustomerMotorcycleForm # Changed from CustomerMotorcycleForm
from service.models import CustomerMotorcycle, ServiceProfile


def admin_process_customer_motorcycle_form(request_post_data, request_files, profile_instance, motorcycle_id=None):
    """
    Processes the AdminCustomerMotorcycleForm data.
    Requires the associated ServiceProfile instance for new motorcycles.
    Returns (form_instance, saved_instance)
    """
    instance = None
    if motorcycle_id:
        try:
            instance = CustomerMotorcycle.objects.get(pk=motorcycle_id)
        except CustomerMotorcycle.DoesNotExist:
            # If a motorcycle_id was provided but not found, return an invalid form
            form = AdminCustomerMotorcycleForm(request_post_data, request_files, instance=None)
            form.add_error(None, "Selected motorcycle not found.")
            return form, None

    # Use AdminCustomerMotorcycleForm
    form = AdminCustomerMotorcycleForm(request_post_data, request_files, instance=instance)
    if form.is_valid():
        motorcycle_instance = form.save(commit=False)
        # The AdminCustomerMotorcycleForm already has a 'service_profile' field.
        # If it's a new motorcycle, we need to ensure the profile_instance is set
        # if the form's service_profile field was not explicitly chosen or is empty.
        # The form's save method for ModelForms will handle the 'service_profile' field if it's in request_post_data.
        # However, for consistency and to ensure a profile is always linked when creating a new one from this flow:
        if not motorcycle_id and not form.cleaned_data.get('service_profile'):
            motorcycle_instance.service_profile = profile_instance
        motorcycle_instance.save()
        form.save_m2m() # For many-to-many fields, if any
        return form, motorcycle_instance
    return form, None

