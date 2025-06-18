# SCOOTER_SHOP/inventory/utils/send_sales_booking_to_mechanicdesk.py

import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist
import datetime
from django.utils import timezone


def send_sales_booking_to_mechanicdesk(sales_booking_instance):
    """
    Sends sales booking details to MechanicDesk by creating a "booking request".
    Given MechanicDesk is service-oriented, significant sales details are
    embedded within the 'note' field for clarity. This version populates
    more fields to satisfy MechanicDesk API requirements and includes debug prints.

    Args:
        sales_booking_instance (SalesBooking): The instance of the SalesBooking model.

    Returns:
        bool: True if the booking request was sent successfully, False otherwise.
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

    # Appointment Time (as drop-off time for MechanicDesk, if available)
    appointment_datetime_str = ""
    appointment_datetime_obj = None
    if sales_booking_instance.appointment_date and sales_booking_instance.appointment_time:
        appointment_datetime_obj = datetime.datetime.combine(
            sales_booking_instance.appointment_date,
            sales_booking_instance.appointment_time
        )
        appointment_datetime_str = appointment_datetime_obj.strftime("%d/%m/%Y %H:%M")
    elif sales_booking_instance.appointment_date:
        # Default to 9 AM if only date is available for drop-off time
        appointment_datetime_obj = datetime.datetime.combine(
            sales_booking_instance.appointment_date,
            datetime.time(9, 0)
        )
        appointment_datetime_str = appointment_datetime_obj.strftime("%d/%m/%Y %H:%M")

    # Pickup Time: Set to same day as drop-off/appointment, but later (e.g., 5 PM)
    pickup_datetime_str = ""
    if appointment_datetime_obj:
        pickup_time_obj = datetime.time(17, 0) # 5:00 PM
        pickup_datetime_combined = datetime.datetime.combine(
            appointment_datetime_obj.date(),
            pickup_time_obj
        )
        pickup_datetime_str = pickup_datetime_combined.strftime("%d/%m/%Y %H:%M")
    else:
        # Fallback if no appointment date is set at all, use current date
        now = timezone.now()
        pickup_datetime_str = now.strftime("%d/%m/%Y 17:00")


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
    
    notes_content += f"\nMotorcycle Details:\n"
    notes_content += f"  Title: {motorcycle.title}\n"
    notes_content += f"  Brand: {motorcycle.brand}\n"
    notes_content += f"  Model: {motorcycle.model}\n"
    notes_content += f"  Year: {motorcycle.year}\n"
    notes_content += f"  Condition: {motorcycle.get_condition_display()}\n"
    notes_content += f"  Vin Number: {motorcycle.vin_number if motorcycle.vin_number else 'N/A'}\n"
    # Populated fields
    notes_content += f"  Engine Size: {motorcycle.engine_size if motorcycle.engine_size else 'N/A'}\n"
    notes_content += f"  Odometer: {motorcycle.odometer if motorcycle.odometer is not None else 'N/A'}\n"
    notes_content += f"  Transmission: {motorcycle.get_transmission_display() if motorcycle.transmission else 'N/A'}\n"
    
    if sales_booking_instance.appointment_date:
        notes_content += f"\nAppointment Requested: {sales_booking_instance.appointment_date.strftime('%d/%m/%Y')}"
        if sales_booking_instance.appointment_time:
            notes_content += f" at {sales_booking_instance.appointment_time.strftime('%H:%M %p')}"
        notes_content += "\n"
        
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
        "registration_number": motorcycle.rego if motorcycle.rego else "", # Use rego if available
        "make": motorcycle.brand if motorcycle.brand else "",
        "model": motorcycle.model if motorcycle.model else "",
        "year": str(motorcycle.year) if motorcycle.year else "",
        "color": "", # No direct field on your Motorcycle model for this
        "transmission": motorcycle.transmission if motorcycle.transmission else "", # Populated
        "vin": motorcycle.vin_number if motorcycle.vin_number else "",
        "fuel_type": "", # No direct field
        "drive_type": "", # No direct field
        "engine_size": str(motorcycle.engine_size) if motorcycle.engine_size else "", # Populated
        "body": "", # No direct field
        "odometer": str(motorcycle.odometer) if motorcycle.odometer is not None else "", # Populated
        "drop_off_time": appointment_datetime_str,
        "pickup_time": pickup_datetime_str, # Now populated with a plausible time
        "note": notes_content,
        "courtesy_vehicle_requested": "false",
    }
    
    mechanicdesk_api_url = "https://www.mechanicdesk.com.au/booking_requests/create_booking"

    print(f"DEBUG: Attempting to send sales booking {sales_booking_instance.sales_booking_reference} to MechanicDesk.")
    print(f"DEBUG: MechanicDesk Payload: {payload}")

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
