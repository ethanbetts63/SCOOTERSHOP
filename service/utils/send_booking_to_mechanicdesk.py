import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist

def send_booking_to_mechanicdesk(service_booking_instance):
    mechanicdesk_token = getattr(settings, 'MECHANICDESK_BOOKING_TOKEN', None)
    if not mechanicdesk_token:
        return False

    try:
        service_profile = service_booking_instance.service_profile
    except ObjectDoesNotExist:
        return False

    try:
        customer_motorcycle = service_booking_instance.customer_motorcycle
        if not customer_motorcycle:
            motorcycle_brand = ""
            motorcycle_model = ""
            motorcycle_year = ""
            motorcycle_rego = ""
        else:
            # Updated to use 'brand' and 'rego' based on customer_motorcycle.py
            motorcycle_brand = customer_motorcycle.brand if hasattr(customer_motorcycle, 'brand') else ""
            motorcycle_model = customer_motorcycle.model if hasattr(customer_motorcycle, 'model') else ""
            motorcycle_year = str(customer_motorcycle.year) if hasattr(customer_motorcycle, 'year') and customer_motorcycle.year is not None else ""
            motorcycle_rego = customer_motorcycle.rego if hasattr(customer_motorcycle, 'rego') else ""

    except ObjectDoesNotExist:
        motorcycle_brand = ""
        motorcycle_model = ""
        motorcycle_year = ""
        motorcycle_rego = ""
    except AttributeError:
        motorcycle_brand = ""
        motorcycle_model = ""
        motorcycle_year = ""
        motorcycle_rego = ""


    drop_off_date_str = service_booking_instance.dropoff_date.strftime("%d/%m/%Y")
    
    pickup_date_str = ""
    if service_booking_instance.estimated_pickup_date:
        pickup_date_str = service_booking_instance.estimated_pickup_date.strftime("%d/%m/%Y")

    customer_notes_combined = service_booking_instance.customer_notes or ""
    if service_booking_instance.dropoff_time:
        customer_notes_combined += f"\nCustomer Preferred Drop-off Time: {service_booking_instance.dropoff_time.strftime('%H:%M')}"

    payload = {
        "token": mechanicdesk_token,
        "name": service_profile.name,
        "email": service_profile.email,
        "phone": service_profile.phone_number,
        
        # Updated variable names here to match MechanicDesk's expected 'name' attributes
        # and reflect the actual fields in your CustomerMotorcycle model.
        "make": motorcycle_brand, # MechanicDesk expects 'make', but your model has 'brand'
        "model": motorcycle_model,
        "year": motorcycle_year,
        "registration_number": motorcycle_rego, # MechanicDesk expects 'registration_number', your model has 'rego'
        
        "drop_off_time": drop_off_date_str,
        "pickup_time": pickup_date_str,
        "note": customer_notes_combined,
    }

    mechanicdesk_api_url = "https://mechanicdesk.com.au/booking_requests/"

    try:
        response = requests.post(mechanicdesk_api_url, data=payload, timeout=10)
        response.raise_for_status()

        return True

    except requests.exceptions.Timeout:
        return False
    except requests.exceptions.RequestException as e:
        return False
    except Exception:
        return False

