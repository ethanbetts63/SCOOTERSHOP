import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist
import datetime # Import datetime for combining date and time

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

    customer_motorcycle = None
    try:
        customer_motorcycle = service_booking_instance.customer_motorcycle
        if not customer_motorcycle:
            print(f"DEBUG: No customer_motorcycle associated with booking ID {service_booking_instance.id}.")
    except ObjectDoesNotExist:
        print(f"DEBUG: CustomerMotorcycle for booking ID {service_booking_instance.id} does not exist.")
    except AttributeError:
        print(f"DEBUG: AttributeError accessing customer_motorcycle for booking ID {service_booking_instance.id}.")


    # --- CHANGE FOR OPTION 1: Use actual dropoff_date for MechanicDesk's drop_off_time field ---
    drop_off_datetime_str = ""
    # Use the actual dropoff_date from your model, combined with dropoff_time
    if service_booking_instance.dropoff_date and service_booking_instance.dropoff_time:
        combined_dropoff_date_with_time = datetime.datetime.combine(
            service_booking_instance.dropoff_date,
            service_booking_instance.dropoff_time
        )
        drop_off_datetime_str = combined_dropoff_date_with_time.strftime("%d/%m/%Y %H:%M")
    elif service_booking_instance.dropoff_date: # If only dropoff_date is available, use a default time
        default_dropoff_time = datetime.time(12, 0) # e.g., 12 PM
        combined_dropoff_date_with_default_time = datetime.datetime.combine(
            service_booking_instance.dropoff_date,
            default_dropoff_time
        )
        drop_off_datetime_str = combined_dropoff_date_with_default_time.strftime("%d/%m/%Y %H:%M")
    else:
        print(f"DEBUG: Missing dropoff_date for booking ID {service_booking_instance.id}. Cannot format drop_off_time for MechanicDesk.")


    # Format pick-up time as "dd/mm/yyyy HH:MM"
    pickup_datetime_str = ""
    if service_booking_instance.estimated_pickup_date:
        default_pickup_time = datetime.time(17, 0) # 5 PM
        combined_pickup = datetime.datetime.combine(
            service_booking_instance.estimated_pickup_date,
            default_pickup_time
        )
        pickup_datetime_str = combined_pickup.strftime("%d/%m/%Y %H:%M")
    else:
        print(f"DEBUG: No estimated_pickup_date for booking ID {service_booking_instance.id}. Cannot format pickup_time.")


    customer_notes_combined = service_booking_instance.customer_notes or ""

    # --- CHANGE FOR OPTION 1: Add actual service_date to notes ---
    if service_booking_instance.service_date:
        service_date_str = service_booking_instance.service_date.strftime("%d/%m/%Y")
        customer_notes_combined += f"\nService Scheduled to Commence On: {service_date_str}"
    
    # Original preferred drop-off time note (if applicable)
    if service_booking_instance.dropoff_time:
        customer_notes_combined += f"\nCustomer Preferred Drop-off Time: {service_booking_instance.dropoff_time.strftime('%H:%M')}"


    # Build the payload with all available fields
    payload = {
        "token": mechanicdesk_token,
        "name": service_profile.name,
        "email": service_profile.email,
        "phone": service_profile.phone_number,
        "street_line": service_profile.address_line_1,
        "suburb": service_profile.city, # Mapping city to suburb as per common practice
        "state": service_profile.state,
        "postcode": service_profile.post_code,
        "note": customer_notes_combined,
        "drop_off_time": drop_off_datetime_str, # Now uses actual dropoff_date
        "pickup_time": pickup_datetime_str,
    }

    # Add motorcycle details if available
    if customer_motorcycle:
        payload.update({
            "registration_number": customer_motorcycle.rego if hasattr(customer_motorcycle, 'rego') else "",
            "make": customer_motorcycle.brand if hasattr(customer_motorcycle, 'brand') else "",
            "model": customer_motorcycle.model if hasattr(customer_motorcycle, 'model') else "",
            "year": str(customer_motorcycle.year) if hasattr(customer_motorcycle, 'year') and customer_motorcycle.year is not None else "",
            "transmission": customer_motorcycle.transmission if hasattr(customer_motorcycle, 'transmission') else "",
            "vin": customer_motorcycle.vin_number if hasattr(customer_motorcycle, 'vin_number') else "",
            "engine_size": customer_motorcycle.engine_size if hasattr(customer_motorcycle, 'engine_size') else "",
            "odometer": str(customer_motorcycle.odometer) if hasattr(customer_motorcycle, 'odometer') and customer_motorcycle.odometer is not None else "",
            # Fields like 'color', 'fuel_type', 'drive_type', 'body' are not directly available in your CustomerMotorcycle model
        })

    mechanicdesk_api_url = "https://www.mechanicdesk.com.au/booking_requests/create_booking"

    # Debug print: Show the payload being sent
    print(f"DEBUG: Sending payload to new MechanicDesk API endpoint: {payload}")

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
