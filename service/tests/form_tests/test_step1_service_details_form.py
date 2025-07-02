from django.test import TestCase
from datetime import date, timedelta

                 
from service.forms import ServiceDetailsForm                                         

                                     
from ..test_helpers.model_factories import ServiceTypeFactory
from service.models import ServiceType                                     

class ServiceDetailsFormTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.active_service_type_1 = ServiceTypeFactory(name="Oil Change", is_active=True)
        cls.active_service_type_2 = ServiceTypeFactory(name="Tire Replacement", is_active=True)
        cls.inactive_service_type = ServiceTypeFactory(name="Engine Rebuild", is_active=False)

                                                       
                                                                                   
        cls.valid_data = {
            'service_type': cls.active_service_type_1.pk,
            'service_date': date.today() + timedelta(days=7),                            
        }
                                                                                     

    def test_form_valid_data(self):
        
        form = ServiceDetailsForm(data=self.valid_data)
                                                                          
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['service_type'], self.active_service_type_1)
        self.assertEqual(form.cleaned_data['service_date'], self.valid_data['service_date'])
                                                                          


    def test_form_invalid_data_missing_fields(self):
        
                                   
        data = self.valid_data.copy()
        data['service_type'] = ''
        form = ServiceDetailsForm(data=data)
                                                 
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('This field is required.', form.errors['service_type'])

                                                               
        data = self.valid_data.copy()
        data['service_date'] = ''
        form = ServiceDetailsForm(data=data)
                                                 
        self.assertFalse(form.is_valid())
        self.assertIn('service_date', form.errors)
        self.assertIn('This field is required.', form.errors['service_date'])

    def test_service_type_queryset(self):
        
        form = ServiceDetailsForm()
                                            
        queryset = form.fields['service_type'].queryset

                                                              
        self.assertIn(self.active_service_type_1, queryset)
        self.assertIn(self.active_service_type_2, queryset)
                                                                      
        self.assertNotIn(self.inactive_service_type, queryset)
                                                   
        self.assertEqual(queryset.count(), ServiceType.objects.filter(is_active=True).count())


    def test_service_date_past_date_validation(self):                                                      
        
                               
        past_date = date.today() - timedelta(days=1)
        data = self.valid_data.copy()
        data['service_date'] = past_date                     
        form = ServiceDetailsForm(data=data)
                                                 
        
        self.assertFalse(form.is_valid())                                       
        self.assertIn('service_date', form.errors)                     
        self.assertIn('Service date cannot be in the past.', form.errors['service_date'])                        

                                                  
        today_date = date.today()
        data = self.valid_data.copy()
        data['service_date'] = today_date                     
        form = ServiceDetailsForm(data=data)
                                                 
        self.assertTrue(form.is_valid(), f"Form is not valid with today's date: {form.errors}")
        self.assertEqual(form.cleaned_data['service_date'], today_date)                     

                                                   
        future_date = date.today() + timedelta(days=1)
        data = self.valid_data.copy()
        data['service_date'] = future_date                     
        form = ServiceDetailsForm(data=data)
                                                 
        self.assertTrue(form.is_valid(), f"Form is not valid with future date: {form.errors}")
        self.assertEqual(form.cleaned_data['service_date'], future_date)                     

    