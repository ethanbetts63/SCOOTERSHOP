from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from service.models import ServiceBooking, BlockedServiceDate


def get_service_bookings_json_ajax(request):
    start_param = request.GET.get('start')
    end_param = request.GET.get('end')

    start_date = None
    end_date = None
    if start_param:
        try:
            start_date = timezone.datetime.fromisoformat(start_param.replace('Z', '+00:00'))
            start_date = timezone.localdate(start_date)
        except ValueError:
            pass
    if end_param:
        try:
            end_date = timezone.datetime.fromisoformat(end_param.replace('Z', '+00:00'))
            end_date = timezone.localdate(end_date)
        except ValueError:
            pass

    events = []

    bookings_query = ServiceBooking.objects.select_related(
        'service_type',
        'service_profile__user',
        'customer_motorcycle'
    )
    if start_date and end_date:
        bookings_query = bookings_query.filter(dropoff_date__range=[start_date, end_date - timedelta(days=1)])

    bookings = bookings_query.all()

    for booking in bookings:
        booking_url = None
        if hasattr(booking, 'pk'):
            try:
                booking_url = reverse('service:admin_service_booking_detail', args=[booking.pk])
            except Exception as e:
                pass

        customer_name = 'N/A'
        if booking.service_profile:
            if booking.service_profile.user and booking.service_profile.user.get_full_name():
                customer_name = booking.service_profile.user.get_full_name()
            elif booking.service_profile.name:
                customer_name = booking.service_profile.name

        vehicle_brand = ''
        vehicle_model = ''
        if booking.customer_motorcycle:
            vehicle_brand = booking.customer_motorcycle.brand
            vehicle_model = booking.customer_motorcycle.model

        event_end_date = booking.estimated_pickup_date if booking.estimated_pickup_date else booking.dropoff_date
        event_end_date_for_fc = (event_end_date + timedelta(days=1)).isoformat()


        events.append({
            'id': booking.pk,
            'title': f"{customer_name} - {booking.service_type.name if booking.service_type else 'Service'}",
            'start': booking.dropoff_date.isoformat(),
            'end': event_end_date_for_fc,
            'url': booking_url,
            'extendedProps': {
                'customer_name': customer_name,
                'vehicle_brand': vehicle_brand,
                'vehicle_model': vehicle_model,
                'service_type': booking.service_type.name if booking.service_type else 'Service',
                'status': booking.booking_status.lower(),
                'is_blocked': False,
            }
        })

    blocked_dates_query = BlockedServiceDate.objects.all()
    if start_date and end_date:
        blocked_dates_query = blocked_dates_query.filter(
            start_date__lte=end_date,
            end_date__gte=start_date
        )
    blocked_dates = blocked_dates_query.all()

    for blocked_date in blocked_dates:
        blocked_event_end_date_for_fc = (blocked_date.end_date + timedelta(days=1)).isoformat()

        events.append({
            'id': f"blocked-{blocked_date.pk}",
            'title': 'Blocked Day',
            'start': blocked_date.start_date.isoformat(),
            'end': blocked_event_end_date_for_fc,
            'extendedProps': {
                'is_blocked': True,
                'description': blocked_date.description,
            },
            'display': 'background',
            'classNames': ['status-blocked'],
        })

    return JsonResponse(events, safe=False)
