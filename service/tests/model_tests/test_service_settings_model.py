from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import time
from service.models import ServiceSettings

class ServiceSettingsModelTest(TestCase):
    def test_latest_service_day_drop_off_validation(self):
        # Test that the latest_service_day_drop_off cannot be before the drop_off_start_time
        with self.assertRaises(ValidationError):
            ServiceSettings.objects.create(
                drop_off_start_time=time(9, 0),
                latest_service_day_drop_off=time(8, 0)
            ).full_clean()

        # Test that the latest_service_day_drop_off cannot be after the drop_off_end_time
        with self.assertRaises(ValidationError):
            ServiceSettings.objects.create(
                drop_off_end_time=time(17, 0),
                latest_service_day_drop_off=time(18, 0)
            ).full_clean()

        # Test that a valid latest_service_day_drop_off can be saved
        settings = ServiceSettings.objects.create(
            drop_off_start_time=time(9, 0),
            drop_off_end_time=time(17, 0),
            latest_service_day_drop_off=time(10, 0)
        )
        self.assertEqual(settings.latest_service_day_drop_off, time(10, 0))