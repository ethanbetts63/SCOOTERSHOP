from service.forms import ServiceBookingUserForm
from service.models import ServiceProfile

def admin_process_service_profile_form(request_post_data, profile_id=None):
    """
    Processes the ServiceProfile form data.
    Returns (form_instance, saved_instance)
    """
    instance = None
    if profile_id:
        try:
            instance = ServiceProfile.objects.get(pk=profile_id)
        except ServiceProfile.DoesNotExist:
            # Handle this error more gracefully, e.g., via form error or raise an exception
            pass # For now, just let form be invalid if instance not found

    form = ServiceBookingUserForm(request_post_data, instance=instance)
    if form.is_valid():
        saved_instance = form.save()
        return form, saved_instance
    return form, None