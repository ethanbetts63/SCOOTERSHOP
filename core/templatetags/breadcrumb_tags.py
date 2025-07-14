from django import template
from django.urls import reverse
import json

register = template.Library()

@register.inclusion_tag('core/partials/breadcrumbs.html', takes_context=True)
def breadcrumbs(context):
    request = context['request']
    path_parts = [part for part in request.path.split('/') if part]
    
    breadcrumbs_list = []
    current_path = '/'

    # Add home breadcrumb
    breadcrumbs_list.append({
        'name': 'Home',
        'url': reverse('core:index') # Assuming 'core:index' is the name for your home URL
    })

    for i, part in enumerate(path_parts):
        current_path += part + '/'
        # Attempt to resolve the URL part to a view name or just use the part itself
        # This is a simplified approach; a more robust solution might involve a mapping
        # or more complex URL resolution.
        try:
            # This part is tricky as reverse needs a view name.
            # For now, we'll just construct the URL directly.
            # A better approach would be to have a lookup for display names and URLs.
            pass
        except:
            pass # Handle cases where part doesn't directly map to a named URL

        # Capitalize and replace hyphens for display name
        display_name = part.replace('-', ' ').replace('_', ' ').title()
        
        # For the last part, it's the current page, so it's not a link
        if i == len(path_parts) - 1:
            breadcrumbs_list.append({
                'name': display_name,
                'url': None # Last item is not a link
            })
        else:
            breadcrumbs_list.append({
                'name': display_name,
                'url': current_path
            })

    # Generate JSON-LD for Schema.org
    json_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": []
    }

    for i, breadcrumb in enumerate(breadcrumbs_list):
        if breadcrumb['url']: # Only include linked items in JSON-LD
            json_ld['itemListElement'].append({
                "@type": "ListItem",
                "position": i + 1,
                "name": breadcrumb['name'],
                "item": request.build_absolute_uri(breadcrumb['url'])
            })
        else: # For the last item (current page), include it without an item URL
             json_ld['itemListElement'].append({
                "@type": "ListItem",
                "position": i + 1,
                "name": breadcrumb['name']
            })

    return {
        'breadcrumbs': breadcrumbs_list,
        'json_ld_breadcrumbs': json.dumps(json_ld, indent=2)
    }
