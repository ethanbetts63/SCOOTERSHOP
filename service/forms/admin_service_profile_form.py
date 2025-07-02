from django import forms
from service.models import ServiceProfile
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminServiceProfileForm(forms.ModelForm):
    
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=False,
        empty_label="-- No User Account --",
        help_text="Optionally link this Service Profile to an existing user account. A user can only be linked to one profile.",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ServiceProfile
        fields = [
            'user',
            'name',
            'email',
            'phone_number',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'post_code',
            'country',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'post_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': 'Linked User Account',
            'name': 'Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'address_line_1': 'Address Line 1',
            'address_line_2': 'Address Line 2 (Optional)',
            'city': 'City',
            'state': 'State/Province',
            'post_code': 'Post Code',
            'country': 'Country',
        }

    def clean_user(self):
        
        user = self.cleaned_data.get('user')

                                
        if user:
                                                                          
            existing_profile_for_user = ServiceProfile.objects.filter(user=user).first()

                                                  
            if existing_profile_for_user:
                                                                       
                                                                                                 
                                                                          
                if self.instance and existing_profile_for_user.pk == self.instance.pk:
                    pass                                                
                else:
                                                                                                
                    raise forms.ValidationError(
                        f"This user ({user.username}) is already linked to another Service Profile."
                    )
        return user

    def clean(self):
        
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')

                                                                                      
        if not user:
            if not name:
                self.add_error('name', "Full Name is required if no user account is linked.")
            if not email:
                self.add_error('email', "Email Address is required if no user account is linked.")
            if not phone_number:
                self.add_error('phone_number', "Phone Number is required if no user account is linked.")

        return cleaned_data
