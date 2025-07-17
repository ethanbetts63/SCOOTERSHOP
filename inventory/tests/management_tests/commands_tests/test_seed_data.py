from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from inventory.models import Motorcycle, FeaturedMotorcycle, MotorcycleCondition


class SeedDataCommandTest(TestCase):
    def setUp(self):
        # Ensure no data exists before each test
        Motorcycle.objects.all().delete()
        FeaturedMotorcycle.objects.all().delete()
        MotorcycleCondition.objects.all().delete()

    def test_seed_all_data_default(self):
        out = StringIO()
        call_command("seed_data", stdout=out)

        self.assertIn("--- Starting Data Seeding Operation ---", out.getvalue())
        self.assertIn("--- Data Seeding Operation Finished ---", out.getvalue())

        self.assertTrue(MotorcycleCondition.objects.exists())
        self.assertTrue(Motorcycle.objects.exists())
        self.assertTrue(FeaturedMotorcycle.objects.exists())

        self.assertEqual(Motorcycle.objects.count(), 15)  # Default count

    def test_seed_motorcycles_only(self):
        out = StringIO()
        call_command("seed_data", type="motorcycles", count=5, stdout=out)

        self.assertTrue(MotorcycleCondition.objects.exists())
        self.assertEqual(Motorcycle.objects.count(), 5)
        self.assertFalse(FeaturedMotorcycle.objects.exists())

    def test_seed_featured_only(self):
        # Need some motorcycles to feature first
        call_command("seed_data", type="motorcycles", count=10, no_clear=True)

        out = StringIO()
        call_command("seed_data", type="featured", stdout=out)

        self.assertTrue(MotorcycleCondition.objects.exists())
        self.assertTrue(Motorcycle.objects.exists())
        self.assertTrue(FeaturedMotorcycle.objects.exists())

        # Check that featured motorcycles were created (up to 10, 5 new, 5 used)
        self.assertGreater(FeaturedMotorcycle.objects.count(), 0)

    def test_seed_no_clear(self):
        call_command("seed_data", type="motorcycles", count=5, no_clear=True)
        initial_motorcycle_count = Motorcycle.objects.count()

        out = StringIO()
        call_command(
            "seed_data", type="motorcycles", count=3, no_clear=True, stdout=out
        )

        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count + 3)
        self.assertIn("Successfully created 3 new motorcycles.", out.getvalue())

    def test_seed_conditions_creation(self):
        MotorcycleCondition.objects.all().delete()  # Ensure no conditions exist
        out = StringIO()
        call_command("seed_data", type="motorcycles", stdout=out)
        self.assertTrue(MotorcycleCondition.objects.filter(name="new").exists())
        self.assertTrue(MotorcycleCondition.objects.filter(name="used").exists())
        self.assertTrue(MotorcycleCondition.objects.filter(name="demo").exists())
        self.assertIn("Checking/Seeding Motorcycle Conditions...", out.getvalue())
