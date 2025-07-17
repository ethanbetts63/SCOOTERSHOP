from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from dashboard.models import SiteSettings


class SiteSettingsModelTest(TestCase):
    def test_singleton_pattern(self):
        # Test that only one instance of SiteSettings can be created.
        SiteSettings.objects.all().delete()
        settings1 = SiteSettings.get_settings()
        self.assertIsNotNone(settings1)

        with self.assertRaises(ImproperlyConfigured):
            SiteSettings.objects.create()

    def test_get_settings_method(self):
        # Test the get_settings method.
        SiteSettings.objects.all().delete()
        settings = SiteSettings.get_settings()
        self.assertIsInstance(settings, SiteSettings)

        settings2 = SiteSettings.get_settings()
        self.assertEqual(settings.pk, settings2.pk)
