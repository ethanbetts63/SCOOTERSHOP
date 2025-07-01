from service.forms import AdminServiceProfileForm                                      
from service.models import ServiceProfile

def admin_process_service_profile_form(request_post_data, profile_id=None):
    """
    Processes the AdminServiceProfileForm data.
    Returns (form_instance, saved_instance)
    """
    instance = None
    if profile_id:
        try:
            instance = ServiceProfile.objects.get(pk=profile_id)
        except ServiceProfile.DoesNotExist:
            form = AdminServiceProfileForm(request_post_data, instance=None)
            form.add_error(None, "Selected customer profile not found.")
            return form, None

                                 
    form = AdminServiceProfileForm(request_post_data, instance=instance)
    if form.is_valid():
        saved_instance = form.save()
        return form, saved_instance
    return form, None