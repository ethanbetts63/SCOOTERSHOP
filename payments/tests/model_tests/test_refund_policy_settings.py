from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from payments.models import RefundPolicySettings


class RefundPolicySettingsModelTests(TestCase):

    def setUp(self):

        RefundPolicySettings.objects.all().delete()

        self.settings = RefundPolicySettings.objects.create()

    def test_singleton_creation_raises_error(self):

        self.assertEqual(RefundPolicySettings.objects.count(), 1)

        with self.assertRaises(ValidationError) as context:
            RefundPolicySettings.objects.create(
                cancellation_full_payment_full_refund_days=10
            )

        self.assertIn(
            "Only one instance of RefundPolicySettings can be created.",
            str(context.exception),
        )

        self.assertEqual(RefundPolicySettings.objects.count(), 1)

    def test_singleton_get_or_create(self):

        self.assertEqual(RefundPolicySettings.objects.count(), 1)
        initial_instance = RefundPolicySettings.objects.get()

        new_settings, created = RefundPolicySettings.objects.get_or_create(pk=1)

        self.assertFalse(created)
        self.assertEqual(RefundPolicySettings.objects.count(), 1)
        self.assertEqual(new_settings.pk, initial_instance.pk)

    def test_default_values(self):

        RefundPolicySettings.objects.all().delete()
        settings = RefundPolicySettings.objects.create()

        self.assertEqual(settings.cancellation_full_payment_full_refund_days, 7)
        self.assertEqual(settings.cancellation_full_payment_partial_refund_days, 3)
        self.assertEqual(
            settings.cancellation_full_payment_partial_refund_percentage,
            Decimal("50.00"),
        )
        self.assertEqual(settings.cancellation_full_payment_minimal_refund_days, 1)
        self.assertEqual(
            settings.cancellation_full_payment_minimal_refund_percentage,
            Decimal("0.00"),
        )

        self.assertEqual(settings.cancellation_deposit_full_refund_days, 7)
        self.assertEqual(settings.cancellation_deposit_partial_refund_days, 3)
        self.assertEqual(
            settings.cancellation_deposit_partial_refund_percentage, Decimal("50.00")
        )
        self.assertEqual(settings.cancellation_deposit_minimal_refund_days, 1)
        self.assertEqual(
            settings.cancellation_deposit_minimal_refund_percentage, Decimal("0.00")
        )

        self.assertTrue(settings.refund_deducts_stripe_fee_policy)
        self.assertEqual(settings.stripe_fee_percentage_domestic, Decimal("0.0170"))
        self.assertEqual(settings.stripe_fee_fixed_domestic, Decimal("0.30"))
        self.assertEqual(
            settings.stripe_fee_percentage_international, Decimal("0.0350")
        )
        self.assertEqual(settings.stripe_fee_fixed_international, Decimal("0.30"))

    def test_str_method(self):

        self.assertEqual(str(self.settings), "Refund Policy Settings")

    def test_percentage_fields_validation_success(self):

        settings = self.settings
        settings.cancellation_full_payment_partial_refund_percentage = Decimal("25.50")
        settings.cancellation_full_payment_minimal_refund_percentage = Decimal("5.00")
        settings.cancellation_deposit_partial_refund_percentage = Decimal("99.99")
        settings.cancellation_deposit_minimal_refund_percentage = Decimal("0.00")
        settings.full_clean()

    def test_percentage_fields_validation_failure_too_high(self):

        settings = self.settings
        settings.cancellation_full_payment_partial_refund_percentage = Decimal("100.01")
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "cancellation_full_payment_partial_refund_percentage",
            cm.exception.message_dict,
        )

    def test_percentage_fields_validation_failure_too_low(self):

        settings = self.settings
        settings.cancellation_full_payment_minimal_refund_percentage = Decimal("-0.01")
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "cancellation_full_payment_minimal_refund_percentage",
            cm.exception.message_dict,
        )

    def test_stripe_fee_percentage_validation_success(self):

        settings = self.settings
        settings.stripe_fee_percentage_domestic = Decimal("0.0500")
        settings.stripe_fee_percentage_international = Decimal("0.0999")
        settings.full_clean()

    def test_stripe_fee_percentage_validation_failure_too_high(self):

        settings = self.settings
        settings.stripe_fee_percentage_domestic = Decimal("0.1001")
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn("stripe_fee_percentage_domestic", cm.exception.message_dict)

    def test_days_thresholds_validation_success(self):

        settings = self.settings

        settings.cancellation_full_payment_full_refund_days = 10
        settings.cancellation_full_payment_partial_refund_days = 5
        settings.cancellation_full_payment_minimal_refund_days = 1

        settings.cancellation_deposit_full_refund_days = 8
        settings.cancellation_deposit_partial_refund_days = 4
        settings.cancellation_deposit_minimal_refund_days = 0
        settings.full_clean()

    def test_days_thresholds_validation_failure_full_payment_order(self):

        settings = self.settings
        settings.cancellation_full_payment_full_refund_days = 2
        settings.cancellation_full_payment_partial_refund_days = 5
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "cancellation_full_payment_full_refund_days", cm.exception.message_dict
        )

        settings = self.settings
        settings.cancellation_full_payment_partial_refund_days = 0
        settings.cancellation_full_payment_minimal_refund_days = 1
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "cancellation_full_payment_partial_refund_days", cm.exception.message_dict
        )

    def test_days_thresholds_validation_failure_deposit_order(self):

        settings = self.settings
        settings.cancellation_deposit_full_refund_days = 2
        settings.cancellation_deposit_partial_refund_days = 5
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "cancellation_deposit_full_refund_days", cm.exception.message_dict
        )

        settings = self.settings
        settings.cancellation_deposit_partial_refund_days = 0
        settings.cancellation_deposit_minimal_refund_days = 1
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn(
            "cancellation_deposit_partial_refund_days", cm.exception.message_dict
        )

    @classmethod
    def tearDownClass(cls):
        RefundPolicySettings.objects.all().delete()
        super().tearDownClass()
