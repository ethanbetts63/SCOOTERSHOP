
from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory
from dashboard.tests.test_helpers.model_factories import ReviewFactory
from dashboard.models import Review

class ReviewDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(is_staff=True)
        self.client.force_login(self.user)
        self.review = ReviewFactory()
        self.url = reverse('dashboard:review_delete', kwargs={'pk': self.review.pk})

    def test_delete_review(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())
