                                    
from django import forms
import datetime

class Step1DateTimeForm(forms.Form):
    pick_up_date = forms.DateField(
        widget=forms.TextInput(attrs={'placeholder': 'Select pick up date', 'class': 'form-control'}),
        label="Pick Up Date"
    )
    pick_up_time = forms.TimeField(
        widget=forms.Select(attrs={'class': 'form-control'}),                                        
        label="Pick Up Time"
    )
    return_date = forms.DateField(
        widget=forms.TextInput(attrs={'placeholder': 'Select return date', 'class': 'form-control'}),
        label="Return Date"
    )
    return_time = forms.TimeField(
        widget=forms.Select(attrs={'class': 'form-control'}),                                        
        label="Return Time"
    )
    has_motorcycle_license = forms.BooleanField(
        required=False, 
        label="I have a motorcycle license",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pick_up_date')
        pickup_time = cleaned_data.get('pick_up_time')
        return_date = cleaned_data.get('return_date')
        return_time = cleaned_data.get('return_time')

        if pickup_date and pickup_time and return_date and return_time:
            pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
            return_datetime = datetime.datetime.combine(return_date, return_time)

            if return_datetime <= pickup_datetime:
                raise forms.ValidationError("Return date and time must be after pickup date and time.")

                                                                                 
                                                                                                

        return cleaned_data