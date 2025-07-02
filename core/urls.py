from django.urls import path                                                                   
from .views import index
from .views.contact_view import ContactView
from .views.privacy_policy_view import PrivacyPolicyView
from .views.returns_policy_view import ReturnsPolicyView
from .views.security_policy_view import SecurityPolicyView
from .views.terms_of_use_view import TermsOfUseView

app_name = 'core'                                   

urlpatterns = [                   
    path('', index, name='index'),                     
    path('contact', ContactView.as_view(), name='contact'),
    path('privacy', PrivacyPolicyView.as_view(), name='privacy'),
    path('returns', ReturnsPolicyView.as_view(), name='returns'),
    path('security', SecurityPolicyView.as_view(), name='security'),
    path('terms', TermsOfUseView.as_view(), name='terms'),
]