from service.forms import AdminCustomerMotorcycleForm
from service.models import CustomerMotorcycle


def admin_process_customer_motorcycle_form(
    request_post_data, request_files, profile_instance, motorcycle_id=None
):
    instance = None
    if motorcycle_id:
        try:
            instance = CustomerMotorcycle.objects.get(pk=motorcycle_id)
        except CustomerMotorcycle.DoesNotExist:
            form = AdminCustomerMotorcycleForm(
                request_post_data, request_files, instance=None
            )
            form.add_error(None, "Selected motorcycle not found.")
            return form, None

    form = AdminCustomerMotorcycleForm(
        request_post_data, request_files, instance=instance
    )
    if form.is_valid():
        motorcycle_instance = form.save(commit=False)

        if not motorcycle_id and not form.cleaned_data.get("service_profile"):
            motorcycle_instance.service_profile = profile_instance
        motorcycle_instance.save()
        form.save_m2m()
        return form, motorcycle_instance
    return form, None
