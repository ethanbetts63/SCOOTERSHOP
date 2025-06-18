# SCOOTER_SHOP/inventory/utils/send_sales_booking_to_mechanicdesk.py

import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist
import datetime
from django.utils import timezone
import pytz # Import the pytz library for timezone handling

def send_sales_booking_to_mechanicdesk(sales_booking_instance):
    """
    Sends sales booking details to MechanicDesk by creating a "booking request".
    This version converts the local Perth time to UTC before sending, as the API
    likely expects UTC time.
    """
    mechanicdesk_token = getattr(settings, 'MECHANICDESK_BOOKING_TOKEN', None)
    if not mechanicdesk_token:
        print("DEBUG: MECHANICDESK_BOOKING_TOKEN not set in settings. Cannot send to MechanicDesk.")
        return False

    try:
        sales_profile = sales_booking_instance.sales_profile
        motorcycle = sales_booking_instance.motorcycle
    except ObjectDoesNotExist:
        print("DEBUG: SalesProfile or Motorcycle not found for sales booking instance. Cannot send to MechanicDesk.")
        return False
    except AttributeError:
        print("DEBUG: Missing attribute (SalesProfile or Motorcycle) on sales booking instance. Cannot send to MechanicDesk.")
        return False

    customer_first_name = sales_profile.name.split(' ')[0] if sales_profile.name else ""
    customer_last_name = ' '.join(sales_profile.name.split(' ')[1:]) if ' ' in sales_profile.name else ""

    # --- Timezone Correction Logic (v2) ---
    # The goal is to send the time to MechanicDesk in UTC.
    try:
        perth_tz = pytz.timezone(settings.TIME_ZONE)
    except pytz.UnknownTimeZoneError:
        print(f"ERROR: The timezone '{settings.TIME_ZONE}' in settings.py is invalid. Defaulting to UTC.")
        perth_tz = pytz.utc

    appointment_datetime_str = ""
    
    # 1. Determine the naive datetime object first from the booking instance
    naive_datetime = None
    if sales_booking_instance.appointment_date and sales_booking_instance.appointment_time:
        naive_datetime = datetime.datetime.combine(
            sales_booking_instance.appointment_date,
            sales_booking_instance.appointment_time
        )
    elif sales_booking_instance.appointment_date:
        naive_datetime = datetime.datetime.combine(
            sales_booking_instance.appointment_date,
            datetime.time(9, 0)  # Default to 9 AM if time not specified
        )

    # 2. Convert to an aware, UTC datetime string for the API
    if naive_datetime:
        # Localize the naive datetime to the Perth timezone, treating the input time as "Perth time"
        perth_time = perth_tz.localize(naive_datetime)
        
        # Convert the Perth time to UTC
        utc_time = perth_time.astimezone(pytz.utc)
        
        # Format the UTC time into the string format required by the API
        appointment_datetime_str = utc_time.strftime("%d/%m/%Y %H:%M")
    else:
        # Fallback: if no appointment date, use current time, convert to UTC and format
        utc_now = timezone.now().astimezone(pytz.utc)
        appointment_datetime_str = utc_now.strftime("%d/%m/%Y %H:%M")

    # Pickup time is set to be the same as drop_off_time
    pickup_datetime_str = appointment_datetime_str
    # --- End of Timezone Correction Logic ---

    # Construct the comprehensive 'note' field
    notes_content = f"--- SALES BOOKING NOTIFICATION ---\n\n"
    notes_content += f"Booking Reference: {sales_booking_instance.sales_booking_reference}\n"
    notes_content += f"Booking Status: {sales_booking_instance.get_booking_status_display()}\n"
    notes_content += f"Customer Name: {sales_profile.name}\n"
    notes_content += f"Customer Email: {sales_profile.email}\n"
    notes_content += f"Customer Phone: {sales_profile.phone_number}\n"
    
    if sales_profile.address_line_1:
        notes_content += f"Customer Address: {sales_profile.address_line_1}"
        if sales_profile.address_line_2:
            notes_content += f", {sales_profile.address_line_2}"
        notes_content += f", {sales_profile.city}, {sales_profile.state} {sales_profile.post_code}, {sales_profile.country}\n"
        
    if sales_booking_instance.appointment_date:
        # The note for the human should contain the actual, local appointment time.
        local_time_str = sales_booking_instance.appointment_time.strftime('%I:%M %p') if sales_booking_instance.appointment_time else "Not specified"
        notes_content += f"\nAppointment Requested (Perth Time): {sales_booking_instance.appointment_date.strftime('%d/%m/%Y')} at {local_time_str}\n"
        
    notes_content += f"\nFinancial Details:\n"
    notes_content += f"  Amount Paid (Deposit): {sales_booking_instance.amount_paid} {sales_booking_instance.currency}\n"
    notes_content += f"  Payment Status: {sales_booking_instance.get_payment_status_display()}\n"
    
    if sales_booking_instance.customer_notes:
        notes_content += f"\nCustomer Notes (from booking): {sales_booking_instance.customer_notes}\n"

    # MechanicDesk API Payload Structure
    payload = {
        "token": mechanicdesk_token,
        "name": sales_profile.name,
        "first_name": customer_first_name,
        "last_name": customer_last_name,
        "phone": sales_profile.phone_number,
        "email": sales_profile.email,
        "street_line": sales_profile.address_line_1 if sales_profile.address_line_1 else "",
        "suburb": sales_profile.city if sales_profile.city else "",
        "state": sales_profile.state if sales_profile.state else "",
        "postcode": sales_profile.post_code if sales_profile.post_code else "",
        "registration_number": motorcycle.rego if motorcycle.rego else "",
        "make": motorcycle.brand if motorcycle.brand else "",
        "model": motorcycle.model if motorcycle.model else "",
        "year": str(motorcycle.year) if motorcycle.year else "",
        "color": "",
        "transmission": motorcycle.transmission if motorcycle.transmission else "",
        "vin": motorcycle.vin_number if motorcycle.vin_number else "",
        "fuel_type": "",
        "drive_type": "",
        "engine_size": str(motorcycle.engine_size) if motorcycle.engine_size else "",
        "body": "",
        "odometer": str(motorcycle.odometer) if motorcycle.odometer is not None else "",
        "drop_off_time": "", # This string is now in UTC
        "pickup_time": "",       # This string is now in UTC
        "note": notes_content,
        "courtesy_vehicle_requested": "false",
    }
    
    mechanicdesk_api_url = "https://www.mechanicdesk.com.au/booking_requests/create_booking"

    print(f"DEBUG: Attempting to send sales booking {sales_booking_instance.sales_booking_reference} to MechanicDesk.")
    print(f"DEBUG: MechanicDesk Payload (time is in UTC): {payload}")

    try:
        response = requests.post(mechanicdesk_api_url, data=payload, timeout=10)
        response.raise_for_status()
        print(f"DEBUG: Sales booking {sales_booking_instance.sales_booking_reference} successfully sent to MechanicDesk. Status: {response.status_code}")
        print(f"DEBUG: MechanicDesk Response: {response.text}")
        return True
    except requests.exceptions.Timeout:
        print(f"ERROR: MechanicDesk API request timed out for sales booking {sales_booking_instance.sales_booking_reference}.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Error sending sales booking {sales_booking_instance.sales_booking_reference} to MechanicDesk: {e}.")
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR: MechanicDesk API Response Content: {e.response.text}")
        return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while sending sales booking {sales_booking_instance.sales_booking_reference} to MechanicDesk: {e}.")
        return False
