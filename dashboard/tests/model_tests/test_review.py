
from django.test import TestCase
from django.core.exceptions import ValidationError
from dashboard.tests.test_helpers.model_factories import ReviewFactory
from dashboard.models.review import Review

class ReviewModelTest(TestCase):
    def test_review_creation(self):
        review = ReviewFactory()
        self.assertIsInstance(review, Review)
        self.assertEqual(str(review), f"Review by {review.author_name} - {review.rating} stars")

    def test_review_ordering(self):
        review1 = ReviewFactory(display_order=1)
        review2 = ReviewFactory(display_order=0)
        reviews = Review.objects.all()
        self.assertEqual(reviews[0], review2)
        self.assertEqual(reviews[1], review1)

    def test_rating_validator(self):
        with self.assertRaises(ValidationError):
            review = ReviewFactory(rating=0)
            review.full_clean()

        with self.assertRaises(ValidationError):
            review = ReviewFactory(rating=6)
            review.full_clean()
