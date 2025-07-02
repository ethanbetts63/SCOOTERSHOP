from django.test import TestCase

                                        
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION

                                     
from ..test_helpers.model_factories import ServiceProfileFactory, CustomerMotorcycleFactory

class MotorcycleSelectionFormTest(TestCase):
    #--

    @classmethod
    def setUpTestData(cls):
        #--
        cls.service_profile_with_bikes = ServiceProfileFactory()
        cls.motorcycle1 = CustomerMotorcycleFactory(
            service_profile=cls.service_profile_with_bikes,
            brand="Honda",
                            
            model="600RR",
            rego="ABC123",
            odometer=10000,                          
            transmission="MANUAL",                              
            engine_size="600cc",                             
        )
        cls.motorcycle2 = CustomerMotorcycleFactory(
            service_profile=cls.service_profile_with_bikes,
            brand="Yamaha",
                            
            model="R1",
            rego="XYZ789",
            odometer=12000,                          
            transmission="MANUAL",                              
            engine_size="1000cc",                             
        )

        cls.service_profile_no_bikes = ServiceProfileFactory()

    def test_form_initialization_with_motorcycles(self):
        #--
        form = MotorcycleSelectionForm(service_profile=self.service_profile_with_bikes)
        choices = form.fields['selected_motorcycle'].choices

                                                                       
                                           
        self.assertEqual(len(choices), 3)                          

                                    
        self.assertEqual(choices[0], (ADD_NEW_MOTORCYCLE_OPTION, "--- Add a New Motorcycle ---"))

                                                                           
        self.assertIn((str(self.motorcycle1.pk), f"{self.motorcycle1.brand} {self.motorcycle1.model} ({self.motorcycle1.rego})"), choices)
        self.assertIn((str(self.motorcycle2.pk), f"{self.motorcycle2.brand} {self.motorcycle2.model} ({self.motorcycle2.rego})"), choices)

                                                                                                                                            
                                                                                                            
        self.assertIsNone(form.fields['selected_motorcycle'].initial)


    def test_form_initialization_without_motorcycles(self):
        #--
        form = MotorcycleSelectionForm(service_profile=self.service_profile_no_bikes)
        choices = form.fields['selected_motorcycle'].choices

                                                                            
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0], (ADD_NEW_MOTORCYCLE_OPTION, "--- Add a New Motorcycle ---"))

                                                         
        self.assertEqual(form.fields['selected_motorcycle'].initial, ADD_NEW_MOTORCYCLE_OPTION)

    def test_form_valid_data_select_existing_motorcycle(self):
        #--
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,
            data={'selected_motorcycle': str(self.motorcycle1.pk)}
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['selected_motorcycle'], str(self.motorcycle1.pk))

    def test_form_valid_data_select_add_new(self):
        #--
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,                                                   
            data={'selected_motorcycle': ADD_NEW_MOTORCYCLE_OPTION}
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['selected_motorcycle'], ADD_NEW_MOTORCYCLE_OPTION)

    def test_form_invalid_data_missing_selection(self):
        #--
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,
            data={'selected_motorcycle': ''}                  
        )
        self.assertFalse(form.is_valid())
        self.assertIn('selected_motorcycle', form.errors)
        self.assertIn('This field is required.', form.errors['selected_motorcycle'])

    def test_form_invalid_data_non_existent_motorcycle_id_format(self):
        #--
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,
            data={'selected_motorcycle': 'not-an-id'}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('selected_motorcycle', form.errors)
                                                                       
        self.assertIn('Select a valid choice. not-an-id is not one of the available choices.', form.errors['selected_motorcycle'])

    def test_form_invalid_data_unowned_motorcycle_id(self):
        #--
                                                                        
        unowned_motorcycle = CustomerMotorcycleFactory(
            brand="Kawasaki", model="Ninja", year=2022, rego="KLM789", odometer=15000,
            transmission="MANUAL", engine_size="400cc"
        )
        
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,                                             
            data={'selected_motorcycle': str(unowned_motorcycle.pk)}                                      
        )
                                                                          
                                                                              
        self.assertFalse(form.is_valid())
        self.assertIn('selected_motorcycle', form.errors)
                                                                
        self.assertIn(f'Select a valid choice. {unowned_motorcycle.pk} is not one of the available choices.', form.errors['selected_motorcycle'])

