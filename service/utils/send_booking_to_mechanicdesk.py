import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist

def send_booking_to_mechanicdesk(service_booking_instance):
    mechanicdesk_token = getattr(settings, 'MECHANICDESK_BOOKING_TOKEN', None)
    if not mechanicdesk_token:
        print("DEBUG: MECHANICDESK_BOOKING_TOKEN not found in settings.")
        return False

    try:
        service_profile = service_booking_instance.service_profile
    except ObjectDoesNotExist:
        print(f"DEBUG: ServiceProfile for booking ID {service_booking_instance.id} does not exist.")
        return False

    try:
        customer_motorcycle = service_booking_instance.customer_motorcycle
        if not customer_motorcycle:
            motorcycle_brand = ""
            motorcycle_model = ""
            motorcycle_year = ""
            motorcycle_rego = ""
            print(f"DEBUG: No customer_motorcycle associated with booking ID {service_booking_instance.id}.")
        else:
            # Updated to use 'brand' and 'rego' based on customer_motorcycle.py
            motorcycle_brand = customer_motorcycle.brand if hasattr(customer_motorcycle, 'brand') else ""
            motorcycle_model = customer_motorcycle.model if hasattr(customer_motorcycle, 'model') else ""
            motorcycle_year = str(customer_motorcycle.year) if hasattr(customer_motorcycle, 'year') and customer_motorcycle.year is not None else ""
            motorcycle_rego = customer_motorcycle.rego if hasattr(customer_motorcycle, 'rego') else ""
            print(f"DEBUG: Customer Motorcycle Details - Brand: {motorcycle_brand}, Model: {motorcycle_model}, Year: {motorcycle_year}, Rego: {motorcycle_rego}")

    except ObjectDoesNotExist:
        print(f"DEBUG: CustomerMotorcycle for booking ID {service_booking_instance.id} does not exist.")
        motorcycle_brand = ""
        motorcycle_model = ""
        motorcycle_year = ""
        motorcycle_rego = ""
    except AttributeError:
        print(f"DEBUG: AttributeError accessing motorcycle details for booking ID {service_booking_instance.id}.")
        motorcycle_brand = ""
        motorcycle_model = ""
        motorcycle_year = ""
        motorcycle_rego = ""


    drop_off_date_str = service_booking_instance.dropoff_date.strftime("%d/%m/%Y")

    pickup_date_str = ""
    if service_booking_instance.estimated_pickup_date:
        pickup_date_str = service_booking_instance.estimated_pickup_date.strftime("%d/%m/%Y")

    customer_notes_combined = service_booking_instance.customer_notes or ""

    # Add drop-off date to notes
    customer_notes_combined += f"\nDrop-off Date: {drop_off_date_str}"

    # Add estimated pickup date to notes
    if pickup_date_str: # Only add if a pickup date exists
        customer_notes_combined += f"\nEstimated Pick-up Date: {pickup_date_str}"

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

        "drop_off_time": drop_off_date_str, # Still send this in case they fix their parsing
        "pickup_time": pickup_date_str,     # Still send this in case they fix their parsing
        "note": customer_notes_combined,
    }

    # Debug print: Show the payload being sent
    print(f"DEBUG: Sending payload to MechanicDesk: {payload}")

    mechanicdesk_api_url = "https://mechanicdesk.com.au/booking_requests/"

    try:
        response = requests.post(mechanicdesk_api_url, data=payload, timeout=10)
        response.raise_for_status()

        # Debug print: Show the response from MechanicDesk
        print(f"DEBUG: MechanicDesk Response Status Code: {response.status_code}")
        print(f"DEBUG: MechanicDesk Response Content: {response.text}")

        return True

    except requests.exceptions.Timeout:
        print(f"DEBUG: Request to MechanicDesk timed out for booking ID {service_booking_instance.id}.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Request to MechanicDesk failed for booking ID {service_booking_instance.id}. Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"DEBUG: MechanicDesk Error Response Status Code: {e.response.status_code}")
            print(f"DEBUG: MechanicDesk Error Response Content: {e.response.text}")
        return False
    except Exception as e:
        print(f"DEBUG: An unexpected error occurred while sending to MechanicDesk for booking ID {service_booking_instance.id}. Error: {e}")
        return False
