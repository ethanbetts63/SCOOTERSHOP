import os
from django.conf import settings
from django.template import Template, Context
from mailer.utils.send_templated_email import send_templated_email

def send_all_test_emails(admin_email):
    template_dir = os.path.join(settings.BASE_DIR, 'mailer', 'templates')
    for template_name in os.listdir(template_dir):
        if template_name.endswith('.html'):
            # Create a dummy context for rendering the template
            context = {
                'booking': None,
                'profile': None,
                'user': None,
                'SITE_DOMAIN': settings.SITE_DOMAIN,
                'SITE_SCHEME': settings.SITE_SCHEME,
            }
            send_templated_email(
                recipient_list=[admin_email],
                subject=f"Test Email: {template_name}",
                template_name=template_name,
                context=context,
                booking=None,
                profile=None,
            )
