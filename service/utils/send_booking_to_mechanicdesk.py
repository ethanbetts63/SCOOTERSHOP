import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist
import datetime
import json

def send_booking_to_mechanicdesk(service_booking_instance):
    mechanicdesk_token = getattr(settings, 'MECHANICDESK_BOOKING_TOKEN', None)
    if not mechanicdesk_token:
        # --- Added for debugging ---
        print("\n--- [MECHANICDESK DEBUG] ---")
        print("  Status: SKIPPED - No MECHANICDESK_BOOKING_TOKEN found in settings.")
        print("--- [END MECHANICDESK DEBUG] ---\n")
        # --- End of debug section ---
        return False

    try:
        service_profile = service_booking_instance.service_profile
    except ObjectDoesNotExist:
        # --- Added for debugging ---
        print("\n--- [MECHANICDESK DEBUG] ---")
        print(f"  Status: FAILED - ServiceProfile does not exist for booking {service_booking_instance.service_booking_reference}.")
        print("--- [END MECHANICDESK DEBUG] ---\n")
        # --- End of debug section ---
        return False

    customer_motorcycle = None
    try:
        customer_motorcycle = service_booking_instance.customer_motorcycle
        if not customer_motorcycle:
            pass
    except ObjectDoesNotExist:
        pass
    except AttributeError:
        pass

    drop_off_datetime_str = ""
    if service_booking_instance.service_date:
        time_for_service = service_booking_instance.dropoff_time or datetime.time(9, 0)
        combined_service_date_with_time = datetime.datetime.combine(
            service_booking_instance.service_date,
            time_for_service
        )
        drop_off_datetime_str = combined_service_date_with_time.strftime("%d/%m/%Y %H:%M")

    pickup_datetime_str = ""
    if service_booking_instance.estimated_pickup_date:
        default_pickup_time = datetime.time(17, 0)
        combined_pickup = datetime.datetime.combine(
            service_booking_instance.estimated_pickup_date,
            default_pickup_time
        )
        pickup_datetime_str = combined_pickup.strftime("%d/%m/%Y %H:%M")

    customer_notes_combined = service_booking_instance.customer_notes or ""
    actual_dropoff_date_str = service_booking_instance.dropoff_date.strftime("%d/%m/%Y")
    customer_notes_combined += f"\nActual Vehicle Drop-off Date: {actual_dropoff_date_str}"
    if service_booking_instance.dropoff_time:
        customer_notes_combined += f"\nCustomer Preferred Drop-off Time: {service_booking_instance.dropoff_time.strftime('%H:%M')}"

    payload = {
        "token": mechanicdesk_token,
        "name": service_profile.name,
        "first_name": service_profile.name.split(' ')[0] if service_profile.name else "",
        "last_name": ' '.join(service_profile.name.split(' ')[1:]) if ' ' in service_profile.name else "",
        "phone": service_profile.phone_number,
        "email": service_profile.email,
        "street_line": service_profile.address_line_1,
        "suburb": service_profile.city,
        "state": service_profile.state,
        "postcode": service_profile.post_code,
        "registration_number": "",
        "make": "",
        "model": "",
        "year": "",
        "color": "",
        "transmission": "",
        "vin": "",
        "fuel_type": "",
        "drive_type": "",
        "engine_size": "",
        "body": "",
        "odometer": "",        "drop_off_time": drop_off_datetime_str,
        "pickup_time": pickup_datetime_str,
        "note": customer_notes_combined,
        "courtesy_vehicle_requested": "false",
    }

    if customer_motorcycle:
        payload.update({
            "registration_number": customer_motorcycle.rego or "",
            "make": customer_motorcycle.brand or "",
            "model": customer_motorcycle.model or "",
            "year": str(customer_motorcycle.year) if customer_motorcycle.year is not None else "",
            "transmission": customer_motorcycle.transmission or "",
            "vin": customer_motorcycle.vin_number or "",
            "engine_size": customer_motorcycle.engine_size or "",
            "odometer": str(customer_motorcycle.odometer) if customer_motorcycle.odometer is not None else "",
        })

    mechanicdesk_api_url = "https://www.mechanicdesk.com.au/booking_requests/create_booking"

    # --- Added for debugging ---
    print("\n--- [MECHANICDESK DEBUG] ---")
    print(f"  Sending booking {service_booking_instance.service_booking_reference} to MechanicDesk...")
    print(f"  API URL: {mechanicdesk_api_url}")
    # Pretty print the payload
    print("  Payload:")
    print(json.dumps(payload, indent=4))
    # --- End of debug section ---

    try:
        response = requests.post(mechanicdesk_api_url, data=payload, timeout=10)
        response.raise_for_status()
        # --- Added for debugging ---
        print("  Response Status Code:", response.status_code)
        print("  Response Text:", response.text)
        print("  Status: SUCCESS")
        print("--- [END MECHANICDESK DEBUG] ---\n")
        # --- End of debug section ---
        return True
    except requests.exceptions.Timeout as e:
        # --- Added for debugging ---
        print(f"  Status: FAILED - Timeout: {e}")
        print("--- [END MECHANICDESK DEBUG] ---\n")
        # --- End of debug section ---
        return False
    except requests.exceptions.RequestException as e:
        # --- Added for debugging ---
        print(f"  Status: FAILED - Request Exception: {e}")
        if e.response:
            print("  Response Status Code:", e.response.status_code)
            print("  Response Text:", e.response.text)
        print("--- [END MECHANICDESK DEBUG] ---\n")
        # --- End of debug section ---
        return False
    except Exception as e:
        # --- Added for debugging ---
        print(f"  Status: FAILED - An unexpected error occurred: {e}")
        print("--- [END MECHANICDESK DEBUG] ---\n")
        # --- End of debug section ---
        return False
