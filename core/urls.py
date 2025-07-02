from django.urls import path                                                                   
from .views import index, contact, privacy_policy, returns_policy, security_policy, terms_of_use

app_name = 'core'                                   

urlpatterns = [                   
    path('', index, name='index'),                     
    path('contact', contact, name='contact'),
    path('privacy', privacy_policy, name='privacy'),
    path('returns', returns_policy, name='returns'),
    path('security', security_policy, name='security'),
    path('terms', terms_of_use, name='terms'),
]