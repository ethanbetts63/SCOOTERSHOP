from django.test import TestCase
from unittest.mock import patch, MagicMock
import datetime

# Import the function to be tested
from service.utils.calculate_estimated_pickup_date import calculate_estimated_pickup_date

# Import factories from the provided model_factories.py
from service.tests.test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceBookingFactory,
    ServiceTypeFactory,
)

class CalculateEstimatedPickupDateTest(TestCase):
    """
    Tests for the calculate_estimated_pickup_date function.
    """

    def setUp(self):
        """
        Set up for each test method.
        """
        # Create a mock ServiceType for testing.
        # We need a ServiceType instance because booking_instance.service_type.estimated_duration is accessed.
        self.service_type_2_days = ServiceTypeFactory(estimated_duration=2)
        self.service_type_5_days = ServiceTypeFactory(estimated_duration=5)
        self.service_type_0_days = ServiceTypeFactory(estimated_duration=0)

        # Fixed service date for consistent testing
        self.fixed_service_date = datetime.date(2025, 6, 15) # Sunday, June 15, 2025

    def test_basic_calculation_temp_service_booking(self):
        """
        Test that the estimated pickup date is correctly calculated and assigned
        for a TempServiceBooking instance with a positive duration.
        """
        # Create a TempServiceBooking instance
        temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_service_date,
            service_type=self.service_type_2_days # Estimated duration of 2 days
        )

        # Mock the save method to check if it's called correctly
        with patch.object(temp_booking, 'save') as mock_save:
            # Call the function to be tested
            calculated_date = calculate_estimated_pickup_date(temp_booking)

            # Expected date: June 15 + 2 days = June 17, 2025
            expected_date = datetime.date(2025, 6, 17)

            # Assert the returned date is correct
            self.assertEqual(calculated_date, expected_date)

            # Assert the booking instance's estimated_pickup_date is updated
            self.assertEqual(temp_booking.estimated_pickup_date, expected_date)

            # Assert the save method was called with the correct update_fields
            mock_save.assert_called_once_with(update_fields=['estimated_pickup_date'])
        
        # Verify the actual saved value (if saving to a real DB, which is not the case here
        # due to patching, but good to know for factory post_generation)
        # Note: If this were a real Django model instance not mocked, you'd fetch it again
        # from the DB to verify the saved value.

    def test_basic_calculation_service_booking(self):
        """
        Test that the estimated pickup date is correctly calculated and assigned
        for a ServiceBooking instance with a positive duration.
        """
        # Create a ServiceBooking instance
        service_booking = ServiceBookingFactory(
            service_date=self.fixed_service_date,
            service_type=self.service_type_5_days # Estimated duration of 5 days
        )

        # Mock the save method
        with patch.object(service_booking, 'save') as mock_save:
            # Call the function to be tested
            calculated_date = calculate_estimated_pickup_date(service_booking)

            # Expected date: June 15 + 5 days = June 20, 2025
            expected_date = datetime.date(2025, 6, 20)

            # Assert the returned date is correct
            self.assertEqual(calculated_date, expected_date)

            # Assert the booking instance's estimated_pickup_date is updated
            self.assertEqual(service_booking.estimated_pickup_date, expected_date)

            # Assert the save method was called with the correct update_fields
            mock_save.assert_called_once_with(update_fields=['estimated_pickup_date'])

    def test_zero_estimated_duration(self):
        """
        Test that the estimated pickup date is the same as the service date
        when the estimated duration is 0 days.
        """
        temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_service_date,
            service_type=self.service_type_0_days # Estimated duration of 0 days
        )

        with patch.object(temp_booking, 'save') as mock_save:
            calculated_date = calculate_estimated_pickup_date(temp_booking)

            # Expected date: June 15 + 0 days = June 15, 2025
            expected_date = self.fixed_service_date

            self.assertEqual(calculated_date, expected_date)
            self.assertEqual(temp_booking.estimated_pickup_date, expected_date)
            mock_save.assert_called_once_with(update_fields=['estimated_pickup_date'])

    def test_no_service_type_attribute(self):
        """
        Test that the function returns None and prints a warning
        when the booking instance has no 'service_type' attribute.
        """
        # Create a mock object that doesn't have a service_type attribute
        mock_booking_instance = MagicMock()
        del mock_booking_instance.service_type # Ensure it does not have the attribute
        mock_booking_instance.service_date = self.fixed_service_date
        mock_booking_instance.save = MagicMock() # Mock save method

        with patch('builtins.print') as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_print.assert_called_once_with(
                f"Warning: Booking instance {mock_booking_instance} has no associated service_type. Cannot calculate estimated pickup date."
            )
            # Ensure save was not called
            mock_booking_instance.save.assert_not_called()

    def test_none_service_type(self):
        """
        Test that the function returns None and prints a warning
        when the booking instance's 'service_type' is None.
        """
        # Create a mock object with service_type set to None
        mock_booking_instance = MagicMock()
        mock_booking_instance.service_type = None
        mock_booking_instance.service_date = self.fixed_service_date
        mock_booking_instance.save = MagicMock() # Mock save method

        with patch('builtins.print') as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_print.assert_called_once_with(
                f"Warning: Booking instance {mock_booking_instance} has no associated service_type. Cannot calculate estimated pickup date."
            )
            # Ensure save was not called
            mock_booking_instance.save.assert_not_called()

    def test_no_service_date_attribute(self):
        """
        Test that the function returns None and prints a warning
        when the booking instance has no 'service_date' attribute.
        """
        # Create a mock object that doesn't have a service_date attribute
        mock_booking_instance = MagicMock()
        mock_booking_instance.service_type = self.service_type_2_days
        del mock_booking_instance.service_date # Ensure it does not have the attribute
        mock_booking_instance.save = MagicMock() # Mock save method

        with patch('builtins.print') as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_print.assert_called_once_with(
                f"Warning: Booking instance {mock_booking_instance} has no service_date. Cannot calculate estimated pickup date."
            )
            # Ensure save was not called
            mock_booking_instance.save.assert_not_called()

    def test_none_service_date(self):
        """
        Test that the function returns None and prints a warning
        when the booking instance's 'service_date' is None.
        """
        # Create a mock object with service_date set to None
        mock_booking_instance = MagicMock()
        mock_booking_instance.service_type = self.service_type_2_days
        mock_booking_instance.service_date = None
        mock_booking_instance.save = MagicMock() # Mock save method

        with patch('builtins.print') as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_print.assert_called_once_with(
                f"Warning: Booking instance {mock_booking_instance} has no service_date. Cannot calculate estimated pickup date."
            )
            # Ensure save was not called
            mock_booking_instance.save.assert_not_called()

    def test_factory_post_generation_for_temp_service_booking(self):
        """
        Verify that the post_generation hook in TempServiceBookingFactory
        correctly calculates the estimated pickup date upon creation.
        """
        # Create a TempServiceBooking instance using the factory.
        # The post_generation hook should call calculate_estimated_pickup_date automatically.
        # We'll use a service type with 3 days duration.
        service_type_3_days = ServiceTypeFactory(estimated_duration=3)
        temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_service_date,
            service_type=service_type_3_days
        )

        # Expected date: June 15 + 3 days = June 18, 2025
        expected_date = datetime.date(2025, 6, 18)

        # Assert that the estimated_pickup_date is set correctly by the factory's post_generation
        self.assertEqual(temp_booking.estimated_pickup_date, expected_date)

    def test_factory_post_generation_for_service_booking(self):
        """
        Verify that the post_generation hook in ServiceBookingFactory
        correctly calculates the estimated pickup date upon creation.
        """
        # Create a ServiceBooking instance using the factory.
        # We'll use a service type with 1 day duration.
        service_type_1_day = ServiceTypeFactory(estimated_duration=1)
        service_booking = ServiceBookingFactory(
            service_date=self.fixed_service_date,
            service_type=service_type_1_day
        )

        # Expected date: June 15 + 1 day = June 16, 2025
        expected_date = datetime.date(2025, 6, 16)

        # Assert that the estimated_pickup_date is set correctly by the factory's post_generation
        self.assertEqual(service_booking.estimated_pickup_date, expected_date)

