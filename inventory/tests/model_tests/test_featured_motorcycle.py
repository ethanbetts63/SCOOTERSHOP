from django.test import TestCase
from inventory.models import FeaturedMotorcycle, Motorcycle
from inventory.tests.test_helpers.model_factories import MotorcycleFactory, FeaturedMotorcycleFactory

class FeaturedMotorcycleModelTest(TestCase):

    def test_featured_motorcycle_creation(self):
        motorcycle = MotorcycleFactory()
        featured = FeaturedMotorcycle.objects.create(
            motorcycle=motorcycle,
            category='new',
            order=1
        )
        self.assertIsInstance(featured, FeaturedMotorcycle)
        self.assertEqual(featured.motorcycle, motorcycle)
        self.assertEqual(featured.category, 'new')
        self.assertEqual(featured.order, 1)

    def test_str_representation(self):
        motorcycle = MotorcycleFactory(title='Test Bike')
        featured = FeaturedMotorcycle.objects.create(
            motorcycle=motorcycle,
            category='used',
            order=1
        )
        self.assertEqual(str(featured), 'Test Bike (Featured Used)')

    def test_ordering(self):
        motorcycle1 = MotorcycleFactory()
        motorcycle2 = MotorcycleFactory()
        motorcycle3 = MotorcycleFactory()

        featured1 = FeaturedMotorcycle.objects.create(motorcycle=motorcycle1, category='new', order=3)
        featured2 = FeaturedMotorcycle.objects.create(motorcycle=motorcycle2, category='new', order=1)
        featured3 = FeaturedMotorcycle.objects.create(motorcycle=motorcycle3, category='new', order=2)

        ordered_featured = list(FeaturedMotorcycle.objects.all())
        self.assertEqual(ordered_featured[0], featured2)
        self.assertEqual(ordered_featured[1], featured3)
        self.assertEqual(ordered_featured[2], featured1)

    def test_category_choices(self):
        featured = FeaturedMotorcycleFactory()
        self.assertIn(featured.category, [choice[0] for choice in FeaturedMotorcycle.CATEGORY_CHOICES])

    def test_related_name(self):
        motorcycle = MotorcycleFactory()
        featured = FeaturedMotorcycleFactory(motorcycle=motorcycle)
        self.assertIn(featured, motorcycle.featured_entries.all())