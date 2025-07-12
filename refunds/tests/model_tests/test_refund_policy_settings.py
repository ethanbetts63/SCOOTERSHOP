from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from refunds.models import RefundSettings


class RefundSettingsModelTests(TestCase):

    def setUp(self):

        RefundSettings.objects.all().delete()

        self.settings = RefundSettings.objects.create()

    def test_singleton_creation_raises_error(self):

        self.assertEqual(RefundSettings.objects.count(), 1)

        with self.assertRaises(ValidationError) as context:
            RefundSettings.objects.create(
                full_payment_full_refund_days=10
            )

        self.assertIn(
            "Only one instance of RefundSettings can be created.",
            str(context.exception),
        )

        self.assertEqual(RefundSettings.objects.count(), 1)

    def test_singleton_get_or_create(self):

        self.assertEqual(RefundSettings.objects.count(), 1)
        initial_instance = RefundSettings.objects.get()

        new_settings, created = RefundSettings.objects.get_or_create(pk=1)

        self.assertFalse(created)
        self.assertEqual(RefundSettings.objects.count(), 1)
        self.assertEqual(new_settings.pk, initial_instance.pk)

    def test_default_values(self):

        RefundSettings.objects.all().delete()
        settings = RefundSettings.objects.create()

        self.assertEqual(settings.full_payment_full_refund_days, 7)
        self.assertEqual(settings.full_payment_partial_refund_days, 3)
        self.assertEqual(
            settings.full_payment_partial_refund_percentage,
            Decimal("50.00"),
        )
        self.assertEqual(settings.full_payment_no_refund_percentage, 1)

        self.assertEqual(settings.deposit_full_refund_days, 7)
        self.assertEqual(settings.deposit_partial_refund_days, 3)
        self.assertEqual(
            settings.deposit_partial_refund_percentage, Decimal("50.00")
        )
        self.assertEqual(settings.deposit_no_refund_days, 1)


    def test_str_method(self):

        self.assertEqual(str(self.settings), "Refund Policy Settings")

    def test_percentage_fields_validation_success(self):

        settings = self.settings
        settings.full_payment_partial_refund_percentage = Decimal("25.50")
        settings.deposit_partial_refund_percentage = Decimal("99.99")
        settings.full_clean()

    def test_percentage_fields_validation_failure_too_high(self):

        settings = self.settings
        settings.full_payment_partial_refund_percentage = Decimal("100.01")
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "full_payment_partial_refund_percentage",
            cm.exception.message_dict,
        )

    def test_days_thresholds_validation_success(self):

        settings = self.settings

        settings.full_payment_full_refund_days = 10
        settings.full_payment_partial_refund_days = 5
        settings.full_payment_no_refund_percentage = 1

        settings.deposit_full_refund_days = 8
        settings.deposit_partial_refund_days = 4
        settings.deposit_no_refund_days = 0
        settings.full_clean()

    def test_days_thresholds_validation_failure_full_payment_order(self):

        settings = self.settings
        settings.full_payment_full_refund_days = 2
        settings.full_payment_partial_refund_days = 5
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "full_payment_full_refund_days", cm.exception.message_dict
        )

        settings = self.settings
        settings.full_payment_partial_refund_days = 0
        settings.full_payment_no_refund_percentage = 1
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "full_payment_partial_refund_days", cm.exception.message_dict
        )

    def test_days_thresholds_validation_failure_deposit_order(self):

        settings = self.settings
        settings.deposit_full_refund_days = 2
        settings.deposit_partial_refund_days = 5
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "deposit_full_refund_days", cm.exception.message_dict
        )

        settings = self.settings
        settings.deposit_partial_refund_days = 0
        settings.deposit_no_refund_days = 1
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "deposit_partial_refund_days", cm.exception.message_dict
        )

    @classmethod
    def tearDownClass(cls):
        RefundSettings.objects.all().delete()
        super().tearDownClass()
