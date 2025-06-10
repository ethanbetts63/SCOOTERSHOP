from django.test import TestCase

# Import the utility function to be tested
from service.utils.admin_parse_booking_request_flags import admin_parse_booking_request_flags

class AdminParseBookingRequestFlagsTest(TestCase):
    """
    Tests for the `admin_parse_booking_request_flags` utility function.
    This suite verifies that the function correctly parses and converts
    hidden flags from a request's POST data.
    """

    def test_all_flags_provided_and_true(self):
        """
        Test parsing when all flags are provided and set to 'true' strings,
        and IDs are provided.
        """
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
        """
        Test parsing when all flags are provided but set to 'false' strings
        or other non-'true' values, and IDs are provided.
        """
        request_data = {
            'selected_profile_id': '789',
            'selected_motorcycle_id': '101',
            'create_new_profile': 'false', # explicit false
            'create_new_motorcycle': '0',   # non-'true' string
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
        """
        Test parsing when some or all flags and IDs are missing from the data.
        They should default to None for IDs and False for booleans.
        """
        request_data = {
            'selected_profile_id': '', # Empty string should result in None
            # selected_motorcycle_id is missing
            'create_new_profile': 'false',
            # create_new_motorcycle is missing
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
        """
        Test parsing with completely empty request data.
        All values should be None or False.
        """
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
        """
        Test behavior when ID values are not strings but convertible to int.
        (Though POST data is usually strings, good to check robustness).
        """
        request_data = {
            'selected_profile_id': 123,  # int instead of string
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
        """
        Test behavior when ID values are strings that cannot be converted to int.
        This should raise a ValueError due to int() conversion.
        """
        request_data = {
            'selected_profile_id': 'invalid_id', # Non-integer string
            'selected_motorcycle_id': '456',
            'create_new_profile': 'true',
            'create_new_motorcycle': 'true',
        }
        with self.assertRaises(ValueError):
            admin_parse_booking_request_flags(request_data)

