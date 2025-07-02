import requests
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from datetime import date, time
import datetime

                                          
from service.utils.send_booking_to_mechanicdesk import send_booking_to_mechanicdesk

                        
                                                                    
from ..test_helpers.model_factories import (
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceBookingFactory,                                                                    
)

                                           
TEST_MECHANICDESK_TOKEN = 'test-token-1234567890abcdef'

class MechanicDeskIntegrationTests(TestCase):
    #--

    @classmethod
    def setUpTestData(cls):
        #--
                                                                                           
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory(
            address_line_1="123 Test St",
            city="Testville",
            state="TS",
            post_code="1234",
            phone_number="0412345678",                               
            name="John Doe"                                                   
        )
        cls.customer_motorcycle = CustomerMotorcycleFactory(
            service_profile=cls.service_profile,
            transmission='AUTOMATIC',
            vin_number='ABC123DEF456GHI78',
            engine_size='500cc',
            odometer=15000,
            brand='Honda',                               
            model='CBR500R',                      
            rego='ABC123'                     
        )

                                                                             
                                                                                

    def setUp(self):
        #--
                                                                                                           
        self.service_booking = ServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
                                                                                 
            service_date=date.today(),
            dropoff_date=date.today() - datetime.timedelta(days=1),                              
            dropoff_time=time(9, 30),
            estimated_pickup_date=date.today() + datetime.timedelta(days=2),
            customer_notes="Regular service and brake check requested."
        )

    @patch('requests.post')                                                                         
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_success(self, mock_post):
        #--
                                                                       
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

                                                                    
        result = send_booking_to_mechanicdesk(self.service_booking)

                    
        self.assertTrue(result)
        mock_post.assert_called_once()

        args, kwargs = mock_post.call_args
                                                       
        self.assertEqual(args[0], "https://www.mechanicdesk.com.au/booking_requests/create_booking")

        sent_data = kwargs['data']

        self.assertEqual(sent_data['token'], TEST_MECHANICDESK_TOKEN)

                                 
        self.assertEqual(sent_data['name'], self.service_profile.name)
        self.assertEqual(sent_data['first_name'], "John")
        self.assertEqual(sent_data['last_name'], "Doe")
        self.assertEqual(sent_data['email'], self.service_profile.email)
        self.assertEqual(sent_data['phone'], self.service_profile.phone_number)

                                         
        self.assertEqual(sent_data['street_line'], self.service_profile.address_line_1)
        self.assertEqual(sent_data['suburb'], self.service_profile.city)
        self.assertEqual(sent_data['state'], self.service_profile.state)
        self.assertEqual(sent_data['postcode'], self.service_profile.post_code)

                                
        self.assertEqual(sent_data['make'], self.customer_motorcycle.brand)
        self.assertEqual(sent_data['model'], self.customer_motorcycle.model)
        self.assertEqual(sent_data['year'], str(self.customer_motorcycle.year))
        self.assertEqual(sent_data['registration_number'], self.customer_motorcycle.rego)
        self.assertEqual(sent_data['transmission'], self.customer_motorcycle.transmission)
        self.assertEqual(sent_data['vin'], self.customer_motorcycle.vin_number)
        self.assertEqual(sent_data['engine_size'], self.customer_motorcycle.engine_size)
        self.assertEqual(sent_data['odometer'], str(self.customer_motorcycle.odometer))

                                                                               
        self.assertEqual(sent_data['color'], "")
        self.assertEqual(sent_data['fuel_type'], "")
        self.assertEqual(sent_data['drive_type'], "")
        self.assertEqual(sent_data['body'], "")


                                                                           
                                                                         
        expected_dropoff_datetime_mechdesk = datetime.datetime.combine(
            self.service_booking.service_date,
            self.service_booking.dropoff_time
        ).strftime("%d/%m/%Y %H:%M")
        self.assertEqual(sent_data['drop_off_time'], expected_dropoff_datetime_mechdesk)

                                                                     
        expected_pickup_datetime = datetime.datetime.combine(
            self.service_booking.estimated_pickup_date,
            datetime.time(17, 0)
        ).strftime("%d/%m/%Y %H:%M")
        self.assertEqual(sent_data['pickup_time'], expected_pickup_datetime)

                                              
        expected_note = (
            f"{self.service_booking.customer_notes}\n"
            f"Actual Vehicle Drop-off Date: {self.service_booking.dropoff_date.strftime('%d/%m/%Y')}\n"
            f"Customer Preferred Drop-off Time: {self.service_booking.dropoff_time.strftime('%H:%M')}"
        )
        self.assertEqual(sent_data['note'], expected_note)
        self.assertEqual(sent_data['courtesy_vehicle_requested'], "false")


    @patch('requests.post')
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_http_error(self, mock_post):
        #--
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid Request Data"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('400 Client Error: Bad Request', response=mock_response)
        mock_post.return_value = mock_response

        result = send_booking_to_mechanicdesk(self.service_booking)

        self.assertFalse(result)
        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch('requests.post')
    @override_settings(MECHANICDESK_BOOKING_TOKEN=None)
    def test_send_booking_to_mechanicdesk_no_token(self, mock_post):
        #--
        result = send_booking_to_mechanicdesk(self.service_booking)

        self.assertFalse(result)
        mock_post.assert_not_called()


    @patch('requests.post')
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_no_customer_motorcycle(self, mock_post):
        #--
        self.service_booking_no_moto = ServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=None,                         
            service_date=date.today(),
            dropoff_date=date.today(),
            dropoff_time=time(10, 0),
            estimated_pickup_date=date.today() + datetime.timedelta(days=2),
            customer_notes="Booking without specific motorcycle."
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        result = send_booking_to_mechanicdesk(self.service_booking_no_moto)

        self.assertTrue(result)
        mock_post.assert_called_once()

        args, kwargs = mock_post.call_args
        sent_data = kwargs['data']

                                                                                                             
        self.assertEqual(sent_data['make'], "")
        self.assertEqual(sent_data['model'], "")
        self.assertEqual(sent_data['year'], "")
        self.assertEqual(sent_data['registration_number'], "")
        self.assertEqual(sent_data['transmission'], "")
        self.assertEqual(sent_data['vin'], "")
        self.assertEqual(sent_data['engine_size'], "")
        self.assertEqual(sent_data['odometer'], "")
        self.assertEqual(sent_data['color'], "")
        self.assertEqual(sent_data['fuel_type'], "")
        self.assertEqual(sent_data['drive_type'], "")
        self.assertEqual(sent_data['body'], "")

                                                                  
        expected_dropoff_datetime_no_moto = datetime.datetime.combine(
            self.service_booking_no_moto.service_date,
            self.service_booking_no_moto.dropoff_time
        ).strftime("%d/%m/%Y %H:%M")
        self.assertEqual(sent_data['drop_off_time'], expected_dropoff_datetime_no_moto)

        expected_pickup_datetime_no_moto = datetime.datetime.combine(
            self.service_booking_no_moto.estimated_pickup_date,
            datetime.time(17, 0)
        ).strftime("%d/%m/%Y %H:%M")
        self.assertEqual(sent_data['pickup_time'], expected_pickup_datetime_no_moto)

        expected_note_no_moto = (
            f"{self.service_booking_no_moto.customer_notes}\n"
            f"Actual Vehicle Drop-off Date: {self.service_booking_no_moto.dropoff_date.strftime('%d/%m/%Y')}\n"
            f"Customer Preferred Drop-off Time: {self.service_booking_no_moto.dropoff_time.strftime('%H:%M')}"
        )
        self.assertEqual(sent_data['note'], expected_note_no_moto)
        self.assertEqual(sent_data['courtesy_vehicle_requested'], "false")
