from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile                        
import os                           

                                                  
from inventory.models import Motorcycle, MotorcycleImage
from django.db import models
                                                                                  
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleImageFactory


class MotorcycleImageModelTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.motorcycle = MotorcycleFactory(brand='TestBrand', model='TestModel', year=2020)
        cls.motorcycle_image = MotorcycleImageFactory(motorcycle=cls.motorcycle)

    def test_motorcycle_image_creation(self):
        
        self.assertIsInstance(self.motorcycle_image, MotorcycleImage)
        self.assertIsNotNone(self.motorcycle_image.pk)                                              

                                             
        self.assertEqual(self.motorcycle_image.motorcycle, self.motorcycle)

    def test_motorcycle_field(self):
        
        field = self.motorcycle_image._meta.get_field('motorcycle')
        self.assertIsInstance(field, type(MotorcycleImage._meta.get_field('motorcycle')))                           
        self.assertEqual(field.related_model, Motorcycle)                      
        self.assertEqual(field._related_name, 'images')                     

    def test_image_field(self):
        
        field = self.motorcycle_image._meta.get_field('image')
        self.assertIsInstance(field, models.FileField)                          
        self.assertEqual(field.upload_to, 'motorcycles/additional/')                       

                                                         
        self.assertTrue(self.motorcycle_image.image)
        self.assertGreater(self.motorcycle_image.image.size, 0)
        

    def test_str_method(self):
        
        expected_str = f"Image for {self.motorcycle}"
        self.assertEqual(str(self.motorcycle_image), expected_str)

    def test_verbose_names_meta(self):
        
        self.assertEqual(MotorcycleImage._meta.verbose_name, "motorcycle image")
        self.assertEqual(MotorcycleImage._meta.verbose_name_plural, "motorcycle images")

