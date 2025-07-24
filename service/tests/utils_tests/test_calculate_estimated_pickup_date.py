from django.test import TestCase
from unittest.mock import patch, MagicMock
import datetime

from service.utils.calculate_estimated_pickup_date import (
    calculate_estimated_pickup_date,
)

from service.tests.test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceBookingFactory,
    ServiceTypeFactory,
)


class CalculateEstimatedPickupDateTest(TestCase):
    def setUp(self):
        self.service_type_2_days = ServiceTypeFactory(estimated_duration_days=2)
        self.service_type_5_days = ServiceTypeFactory(estimated_duration_days=5)
        self.service_type_0_days = ServiceTypeFactory(estimated_duration_days=0)

        self.fixed_service_date = datetime.date(2025, 6, 15)

    def test_basic_calculation_temp_service_booking(self):
        temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_service_date, service_type=self.service_type_2_days
        )

        with patch.object(temp_booking, "save") as mock_save:
            calculated_date = calculate_estimated_pickup_date(temp_booking)

            expected_date = datetime.date(2025, 6, 17)

            self.assertEqual(calculated_date, expected_date)

            self.assertEqual(temp_booking.estimated_pickup_date, expected_date)

            mock_save.assert_called_once_with(update_fields=["estimated_pickup_date"])

    def test_basic_calculation_service_booking(self):
        service_booking = ServiceBookingFactory(
            service_date=self.fixed_service_date, service_type=self.service_type_5_days
        )

        with patch.object(service_booking, "save") as mock_save:
            calculated_date = calculate_estimated_pickup_date(service_booking)

            expected_date = datetime.date(2025, 6, 20)

            self.assertEqual(calculated_date, expected_date)

            self.assertEqual(service_booking.estimated_pickup_date, expected_date)

            mock_save.assert_called_once_with(update_fields=["estimated_pickup_date"])

    def test_zero_estimated_duration_days(self):
        temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_service_date, service_type=self.service_type_0_days
        )

        with patch.object(temp_booking, "save") as mock_save:
            calculated_date = calculate_estimated_pickup_date(temp_booking)

            expected_date = self.fixed_service_date

            self.assertEqual(calculated_date, expected_date)
            self.assertEqual(temp_booking.estimated_pickup_date, expected_date)
            mock_save.assert_called_once_with(update_fields=["estimated_pickup_date"])

    def test_no_service_type_attribute(self):
        mock_booking_instance = MagicMock()
        del mock_booking_instance.service_type
        mock_booking_instance.service_date = self.fixed_service_date
        mock_booking_instance.save = MagicMock()

        with patch("builtins.print") as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_booking_instance.save.assert_not_called()

    def test_none_service_type(self):
        mock_booking_instance = MagicMock()
        mock_booking_instance.service_type = None
        mock_booking_instance.service_date = self.fixed_service_date
        mock_booking_instance.save = MagicMock()

        with patch("builtins.print") as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_booking_instance.save.assert_not_called()

    def test_no_service_date_attribute(self):
        mock_booking_instance = MagicMock()
        mock_booking_instance.service_type = self.service_type_2_days
        del mock_booking_instance.service_date
        mock_booking_instance.save = MagicMock()

        with patch("builtins.print") as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_booking_instance.save.assert_not_called()

    def test_none_service_date(self):
        mock_booking_instance = MagicMock()
        mock_booking_instance.service_type = self.service_type_2_days
        mock_booking_instance.service_date = None
        mock_booking_instance.save = MagicMock()

        with patch("builtins.print") as mock_print:
            calculated_date = calculate_estimated_pickup_date(mock_booking_instance)

            self.assertIsNone(calculated_date)
            mock_booking_instance.save.assert_not_called()

    def test_factory_post_generation_for_temp_service_booking(self):
        service_type_3_days = ServiceTypeFactory(estimated_duration_days=3)
        temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_service_date, service_type=service_type_3_days
        )

        expected_date = datetime.date(2025, 6, 18)

        self.assertEqual(temp_booking.estimated_pickup_date, expected_date)

    def test_factory_post_generation_for_service_booking(self):
        service_type_1_day = ServiceTypeFactory(estimated_duration_days=1)
        service_booking = ServiceBookingFactory(
            service_date=self.fixed_service_date, service_type=service_type_1_day
        )

        expected_date = datetime.date(2025, 6, 16)

        self.assertEqual(service_booking.estimated_pickup_date, expected_date)
