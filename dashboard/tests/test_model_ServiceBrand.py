from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from io import BytesIO
from PIL import Image
from django.db import connection
from dashboard.models import ServiceBrand

class ServiceBrandModelTest(TestCase):

    def setUp(self):
        self.test_image = self._create_test_image()

    def _create_test_image(self, format='JPEG'):
        image_file = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_file, format=format)
        image_file.seek(0)

        return SimpleUploadedFile(f"test_image.{format.lower()}",
                                 image_file.read(),
                                 content_type=f'image/{format.lower()}')

    def test_create_service_brand(self):
        brand = ServiceBrand.objects.create(name="Test Brand")
        self.assertEqual(brand.name, "Test Brand")
        self.assertFalse(brand.is_primary)
        self.assertIsNone(brand.image.name)

    def test_create_primary_brand_with_image(self):
        brand = ServiceBrand.objects.create(
            name="Primary Brand",
            is_primary=True,
            image=self.test_image
        )
        self.assertEqual(brand.name, "Primary Brand")
        self.assertTrue(brand.is_primary)
        self.assertNotEqual(brand.image.name, '')
        brand.image.delete()

    def test_max_primary_brands_limit(self):
        for i in range(5):
            ServiceBrand.objects.create(
                name=f"Primary Brand {i}",
                is_primary=True,
                image=self._create_test_image()
            )

        self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), 5)

        with self.assertRaises(ValueError):
            ServiceBrand.objects.create(
                name="Sixth Primary Brand",
                is_primary=True,
                image=self._create_test_image()
            )

    def test_update_to_primary_exceeding_limit(self):
        for i in range(5):
            ServiceBrand.objects.create(
                name=f"Primary Brand {i}",
                is_primary=True,
                image=self._create_test_image()
            )

        non_primary = ServiceBrand.objects.create(
            name="Non-Primary Brand",
            is_primary=False
        )

        non_primary.is_primary = True
        non_primary.image = self._create_test_image()

        with self.assertRaises(ValueError):
            non_primary.save()

    def test_update_existing_primary_brand(self):
        brands = []
        for i in range(5):
            brand = ServiceBrand.objects.create(
                name=f"Primary Brand {i}",
                is_primary=True,
                image=self._create_test_image()
            )
            brands.append(brand)

        brands[0].name = "Updated Primary Brand"
        brands[0].save()

        updated_brand = ServiceBrand.objects.get(pk=brands[0].pk)
        self.assertEqual(updated_brand.name, "Updated Primary Brand")

    def test_unique_name_constraint(self):
        from django.db import transaction

        ServiceBrand.objects.create(name="Unique Brand")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceBrand.objects.create(name="Unique Brand")

    def test_name_max_length(self):
        from django.core.exceptions import ValidationError

        brand = ServiceBrand(name="A" * 101)
        with self.assertRaises(ValidationError):
            brand.full_clean()

    def test_string_representation(self):
        brand = ServiceBrand.objects.create(name="String Rep Test")
        self.assertEqual(str(brand), "String Rep Test")

    def test_last_updated_auto_now(self):
        brand = ServiceBrand.objects.create(name="Auto Now Test")
        self.assertIsNotNone(brand.last_updated)

    def tearDown(self):
        try:
            for brand in ServiceBrand.objects.all():
                if brand.image and brand.image.name:
                    brand.image.delete(save=False)
            ServiceBrand.objects.all().delete()
        except Exception as e:
            pass
