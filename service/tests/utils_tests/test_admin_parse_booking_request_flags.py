from django.test import TestCase

                                          
from service.utils.admin_parse_booking_request_flags import admin_parse_booking_request_flags

class AdminParseBookingRequestFlagsTest(TestCase):
    

    def test_all_flags_provided_and_true(self):
        
        request_data = {
            'selected_profile_id': '123',
            'selected_motorcycle_id': '456',
            'create_new_profile': 'true',
            'create_new_motorcycle': 'true',
        }
        parsed_flags = admin_parse_booking_request_flags(request_data)

        expected_flags = {
            'selected_profile_id': 123,
            'selected_motorcycle_id': 456,
            'create_new_profile': True,
            'create_new_motorcycle': True,
        }
        self.assertEqual(parsed_flags, expected_flags)

    def test_all_flags_provided_and_false(self):
        
        request_data = {
            'selected_profile_id': '789',
            'selected_motorcycle_id': '101',
            'create_new_profile': 'false',                 
            'create_new_motorcycle': '0',                      
        }
        parsed_flags = admin_parse_booking_request_flags(request_data)

        expected_flags = {
            'selected_profile_id': 789,
            'selected_motorcycle_id': 101,
            'create_new_profile': False,
            'create_new_motorcycle': False,
        }
        self.assertEqual(parsed_flags, expected_flags)

    def test_missing_flags_and_ids(self):
        
        request_data = {
            'selected_profile_id': '',                                     
                                               
            'create_new_profile': 'false',
                                              
        }
        parsed_flags = admin_parse_booking_request_flags(request_data)

        expected_flags = {
            'selected_profile_id': None,
            'selected_motorcycle_id': None,
            'create_new_profile': False,
            'create_new_motorcycle': False,
        }
        self.assertEqual(parsed_flags, expected_flags)

    def test_empty_request_data(self):
        
        request_data = {}
        parsed_flags = admin_parse_booking_request_flags(request_data)

        expected_flags = {
            'selected_profile_id': None,
            'selected_motorcycle_id': None,
            'create_new_profile': False,
            'create_new_motorcycle': False,
        }
        self.assertEqual(parsed_flags, expected_flags)

    def test_non_string_id_values(self):
        
        request_data = {
            'selected_profile_id': 123,                         
            'selected_motorcycle_id': 456,
            'create_new_profile': 'true',
            'create_new_motorcycle': 'false',
        }
        parsed_flags = admin_parse_booking_request_flags(request_data)

        expected_flags = {
            'selected_profile_id': 123,
            'selected_motorcycle_id': 456,
            'create_new_profile': True,
            'create_new_motorcycle': False,
        }
        self.assertEqual(parsed_flags, expected_flags)

    def test_id_values_that_cannot_be_converted_to_int(self):
        
        request_data = {
            'selected_profile_id': 'invalid_id',                     
            'selected_motorcycle_id': '456',
            'create_new_profile': 'true',
            'create_new_motorcycle': 'true',
        }
        with self.assertRaises(ValueError):
            admin_parse_booking_request_flags(request_data)

