
from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory
from dashboard.tests.test_helpers.model_factories import ReviewFactory
from dashboard.models import Review

class ReviewsManagementViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(is_staff=True)
        self.client.force_login(self.user)
        self.review1 = ReviewFactory(display_order=1)
        self.review2 = ReviewFactory(display_order=0)
        self.url = reverse('dashboard:reviews_management')

    def test_get_reviews_management_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/reviews_management.html')
        self.assertEqual(list(response.context['reviews']), [self.review2, self.review1])

    def test_post_increment_display_order(self):
        initial_order = self.review1.display_order
        response = self.client.post(self.url, {'review_id': self.review1.id, 'action': 'increment'})
        self.assertEqual(response.status_code, 302)
        self.review1.refresh_from_db()
        self.assertEqual(self.review1.display_order, initial_order + 1)

    def test_post_decrement_display_order(self):
        initial_order = self.review1.display_order
        response = self.client.post(self.url, {'review_id': self.review1.id, 'action': 'decrement'})
        self.assertEqual(response.status_code, 302)
        self.review1.refresh_from_db()
        self.assertEqual(self.review1.display_order, initial_order - 1)
