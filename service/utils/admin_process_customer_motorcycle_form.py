from service.forms import CustomerMotorcycleForm
from service.models import CustomerMotorcycle


def admin_process_customer_motorcycle_form(request_post_data, request_files, profile_instance, motorcycle_id=None):
    """
    Processes the CustomerMotorcycle form data.
    Requires the associated ServiceProfile instance for new motorcycles.
    Returns (form_instance, saved_instance)
    """
    instance = None
    if motorcycle_id:
        try:
            instance = CustomerMotorcycle.objects.get(pk=motorcycle_id)
        except CustomerMotorcycle.DoesNotExist:
            # Handle error
            pass

    form = CustomerMotorcycleForm(request_post_data, request_files, instance=instance)
    if form.is_valid():
        motorcycle_instance = form.save(commit=False)
        if not motorcycle_id: # Only assign profile if it's a new motorcycle
            motorcycle_instance.customer_profile = profile_instance
        motorcycle_instance.save()
        form.save_m2m() # For many-to-many fields, if any
        return form, motorcycle_instance
    return form, None