                                              
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from hire.models import HireBooking
from payments.models import Payment
                                                            

class BookingConfirmationView(View):
    def get(self, request):
        """
        Displays the booking confirmation details after successful payment.
        It can retrieve the HireBooking either from the session's booking_reference
        (for in-store payments) or from a payment_intent_id passed in the URL query parameters
        (for online payments).
        """
        hire_booking = None
        is_processing = False                                                                  

                                                                                                  
        booking_reference = request.session.get('final_booking_reference')
        if booking_reference:
            try:
                                                                               
                hire_booking = HireBooking.objects.get(booking_reference=booking_reference)
            except HireBooking.DoesNotExist:
                pass                                          
        
                                                                                                            
        payment_intent_id = request.GET.get('payment_intent_id')
        if not hire_booking and payment_intent_id:
            try:
                                                                                         
                hire_booking = HireBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

                                                                                          
                                                                           
                request.session['final_booking_reference'] = hire_booking.booking_reference

            except HireBooking.DoesNotExist:
                is_processing = True                                   
            except Exception as e:
                                                                                              
                is_processing = True
        elif not hire_booking and not payment_intent_id and not booking_reference:                                             
            return redirect('hire:step2_choose_bike')


                                                                                       
                                                                                               
        if not hire_booking and is_processing:
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'hire/step7_booking_confirmation.html', context)
        elif not hire_booking:                                                                        
            return redirect('hire:step2_choose_bike')

                                                                        
        if 'temp_booking_id' in request.session:
            del request.session['temp_booking_id']

        context = {
            'hire_booking': hire_booking,
            'booking_status': hire_booking.status,
            'payment_status': hire_booking.payment_status,
            'grand_total': hire_booking.grand_total,
            'amount_paid': hire_booking.amount_paid,
            'currency': hire_booking.currency,
            'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
            'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
            'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
            'driver_name': hire_booking.driver_profile.name,
            'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
            'addons': hire_booking.booking_addons.all(),
            'is_processing': False,
        }
        return render(request, 'hire/step7_booking_confirmation.html', context)


class BookingStatusCheckView(View):
    def get(self, request):
        """
        AJAX endpoint to check the status of a HireBooking based on payment_intent_id.
        Returns JSON indicating if the booking is ready or still processing.
        """
        payment_intent_id = request.GET.get('payment_intent_id')

        if not payment_intent_id:
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required'}, status=400)

        try:
                                                                                     
            hire_booking = HireBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

                                                         
            response_data = {
                'status': 'ready',
                'booking_reference': hire_booking.booking_reference,
                'booking_status': hire_booking.status,
                'payment_status': hire_booking.payment_status,
                'grand_total': str(hire_booking.grand_total),
                'amount_paid': str(hire_booking.amount_paid),
                'currency': hire_booking.currency,
                'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
                'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
                'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
                'driver_name': hire_booking.driver_profile.name,
                'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
                'addons': [{'name': addon.addon.name, 'quantity': addon.quantity, 'price': str(addon.booked_addon_price)} for addon in hire_booking.booking_addons.all()],
            }
            return JsonResponse(response_data)

        except HireBooking.DoesNotExist:
                                                                                    
                                                                                                                   
            try:
                Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                return JsonResponse({'status': 'processing', 'message': 'Booking still being finalized.'})
            except Payment.DoesNotExist:
                                                                                                       
                                                                                    
                                                                                           
                                                                    
                return JsonResponse({'status': 'error', 'message': 'Booking finalization failed. Please contact support.'}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'An internal server error occurred during status check.'}, status=500)
