
from django.test import TestCase
from dashboard.forms import ReviewForm

class ReviewFormTest(TestCase):
    def test_review_form_valid(self):
        form_data = {
            'author_name': 'Test Author',
            'rating': 5,
            'text': 'This is a test review.',
            'display_order': 1,
            'is_active': True,
        }
        form = ReviewForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_review_form_invalid(self):
        form_data = {
            'author_name': '',
            'rating': 6,
            'text': '',
            'display_order': -1,
        }
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('author_name', form.errors)
        self.assertIn('rating', form.errors)
        self.assertIn('text', form.errors)
