from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.db import models
from dashboard.models import Notification
from dashboard.tests.test_helpers.model_factories import NotificationFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory


class NotificationModelTest(TestCase):
    def setUp(self):
        self.sales_booking = SalesBookingFactory()
        self.notification = Notification.objects.first()

    def test_notification_creation(self):
        self.assertIsInstance(self.notification, Notification)
        self.assertEqual(Notification.objects.count(), 1)

    def test_content_type_field(self):
        field = self.notification._meta.get_field("content_type")
        self.assertEqual(field.related_model, ContentType)
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

    def test_object_id_field(self):
        self.assertEqual(self.notification.object_id, self.sales_booking.pk)

    def test_content_object_field(self):
        self.assertEqual(self.notification.content_object, self.sales_booking)

    def test_message_field(self):
        field = self.notification._meta.get_field("message")
        self.assertEqual(field.max_length, 255)

    def test_created_at_field(self):
        field = self.notification._meta.get_field("created_at")
        self.assertTrue(field.auto_now_add)

    def test_is_cleared_field(self):
        field = self.notification._meta.get_field("is_cleared")
        self.assertFalse(self.notification.is_cleared)
        self.assertFalse(field.default)

    def test_str_method(self):
        self.assertEqual(str(self.notification), self.notification.message)

    def test_meta_options(self):
        self.assertEqual(Notification._meta.ordering, ["-created_at"])
        self.assertEqual(Notification._meta.verbose_name, "Notification")
        self.assertEqual(Notification._meta.verbose_name_plural, "Notifications")