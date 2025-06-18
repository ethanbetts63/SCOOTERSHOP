# SCOOTER_SHOP/inventory/utils/send_sales_booking_to_mechanicdesk.py

import requests
from django.conf import settings
from django.db.models import ObjectDoesNotExist
import datetime

def send_sales_booking_to_mechanicdesk(sales_booking_instance):
    mechanicdesk_token = getattr(settings, 'MECHANICDESK_BOOKING_TOKEN', None)
    if not mechanicdesk_token:
        return False

    try:
        sales_profile = sales_booking_instance.sales_profile
        motorcycle = sales_booking_instance.motorcycle
    except ObjectDoesNotExist:
        return False
    except AttributeError:
        return False

    customer_first_name = sales_profile.name.split(' ')[0] if sales_profile.name else ""
    customer_last_name = ' '.join(sales_profile.name.split(' ')[1:]) if ' ' in sales_profile.name else ""

    appointment_datetime_str = ""
    if sales_booking_instance.appointment_date and sales_booking_instance.appointment_time:
        combined_appointment_datetime = datetime.datetime.combine(
            sales_booking_instance.appointment_date,
            sales_booking_instance.appointment_time
        )
        appointment_datetime_str = combined_appointment_datetime.strftime("%d/%m/%Y %H:%M")
    elif sales_booking_instance.appointment_date:
        combined_appointment_datetime = datetime.datetime.combine(
            sales_booking_instance.appointment_date,
            datetime.time(9, 0)
        )
        appointment_datetime_str = combined_appointment_datetime.strftime("%d/%m/%Y %H:%M")


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
        "registration_number": "",
        "make": motorcycle.brand if motorcycle.brand else "",
        "model": motorcycle.model if motorcycle.model else "",
        "year": str(motorcycle.year) if motorcycle.year else "",
        "color": "",
        "transmission": "",
        "vin": motorcycle.vin_number if motorcycle.vin_number else "",
        "fuel_type": "",
        "drive_type": "",
        "engine_size": "",
        "body": "",
        "odometer": "",
        "drop_off_time": appointment_datetime_str,
        "pickup_time": "",
        "note": notes_content,
        "courtesy_vehicle_requested": "false",
    }
    
    mechanicdesk_api_url = "https://www.mechanicdesk.com.au/booking_requests/create_booking"

    try:
        response = requests.post(mechanicdesk_api_url, data=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.Timeout:
        return False
    except requests.exceptions.RequestException as e:
        return False
    except Exception as e:
        return False

