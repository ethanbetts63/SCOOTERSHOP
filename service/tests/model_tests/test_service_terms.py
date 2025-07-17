from django.test import TestCase
from service.models import ServiceTerms
from service.tests.test_helpers.model_factories import ServiceTermsFactory
from django.core.exceptions import ValidationError


class ServiceTermsModelTest(TestCase):
    def test_service_terms_creation(self):
        terms = ServiceTerms.objects.create(content="Test content")
        self.assertIsInstance(terms, ServiceTerms)
        self.assertEqual(terms.content, "Test content")
        self.assertEqual(terms.version_number, 1)
        self.assertTrue(terms.is_active)

    def test_new_version_becomes_active_and_archives_old(self):
        old_terms = ServiceTermsFactory(is_active=True, version_number=1)
        new_terms = ServiceTerms.objects.create(content="New content", is_active=True)

        old_terms.refresh_from_db()
        self.assertFalse(old_terms.is_active)
        self.assertTrue(new_terms.is_active)
        self.assertEqual(new_terms.version_number, 2)

    def test_str_representation(self):
        terms = ServiceTermsFactory(version_number=5, is_active=True)
        self.assertIn("v5", str(terms))
        self.assertIn("Active", str(terms))

        terms.is_active = False
        terms.save()
        self.assertIn("Archived", str(terms))

    def test_cannot_deactivate_only_active_version(self):
        active_terms = ServiceTermsFactory(is_active=True)

        with self.assertRaises(ValidationError) as cm:
            active_terms.is_active = False
            active_terms.full_clean()  # This calls clean method
            active_terms.save()

        self.assertIn(
            "You cannot deactivate the only active Service Terms version. Please activate another version first.",
            str(cm.exception),
        )

    def test_deactivate_when_multiple_active_versions_exists(self):
        active_terms1 = ServiceTermsFactory(is_active=True)
        active_terms2 = ServiceTermsFactory(is_active=True)

        active_terms1.is_active = False
        active_terms1.full_clean()
        active_terms1.save()

        active_terms1.refresh_from_db()
        active_terms2.refresh_from_db()

        self.assertFalse(active_terms1.is_active)
        self.assertTrue(active_terms2.is_active)

    def test_deactivate_with_another_active_version_already_committed(self):
        # Create two active terms, ensuring both are committed before attempting deactivation
        active_terms_a = ServiceTerms.objects.create(
            content="Content A", is_active=True
        )
        active_terms_b = ServiceTerms.objects.create(
            content="Content B", is_active=True
        )

        # Now, deactivate the first one. It should pass because active_terms_b exists.
        active_terms_a.is_active = False
        active_terms_a.full_clean()
        active_terms_a.save()

        active_terms_a.refresh_from_db()
        active_terms_b.refresh_from_db()

        self.assertFalse(active_terms_a.is_active)
        self.assertTrue(active_terms_b.is_active)

    def test_version_number_auto_increment(self):
        ServiceTerms.objects.all().delete()  # Clear existing to ensure fresh start
        terms1 = ServiceTerms.objects.create(content="Content 1")
        terms2 = ServiceTerms.objects.create(content="Content 2")
        terms3 = ServiceTerms.objects.create(content="Content 3")

        self.assertEqual(terms1.version_number, 1)
        self.assertEqual(terms2.version_number, 2)
        self.assertEqual(terms3.version_number, 3)
