from django.test import TestCase, Client
from django.urls import reverse
from dashboard.models import Review
from dashboard.tests.test_helpers.model_factories import ReviewFactory, UserFactory


class ReviewAddViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create()
        self.client.login(username=self.user.username, password='default_password')

    def test_add_review(self):
        self.assertEqual(Review.objects.count(), 0)
        review_data = ReviewFactory.build()
        response = self.client.post(reverse('dashboard:review_create'), {
            'author_name': review_data.author_name,
            'rating': review_data.rating,
            'text': review_data.text,
            'profile_photo_url': review_data.profile_photo_url,
            'display_order': review_data.display_order,
            'is_active': review_data.is_active,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)