from django import template
from django.urls import reverse
import json

register = template.Library()


@register.simple_tag(takes_context=True)
def get_breadcrumbs(context):
    request = context["request"]
    path_parts = [part for part in request.path.split("/") if part]

    breadcrumbs_list = []
    current_path = "/"

    breadcrumbs_list.append({"name": "Home", "url": reverse("core:index")})

    IGNORED_SLUGS = [
        "service-book",
        "step1",
        "step2",
        "step3",
        "step4",
        "step5",
        "step6",
        "step7",
        "step8",
        "step9",
        "step10",
        "inventory",
        "motorcycles",
        "refunds",
    ]

    for i, part in enumerate(path_parts):
        if part in IGNORED_SLUGS:
            continue

        current_path += part + "/"

        display_name_map = {
            "service": "Service",
            "new": "New Bikes",
            "used": "Used Bikes",
            "contact": "Contact Us",
            "privacy": "Privacy Policy",
            "returns": "Returns Policy",
            "security": "Security Policy",
            "terms": "Terms of Use",
            "enquiries": "Enquiries",
            "dashboard": "Dashboard",
            "login": "Login",
            "register": "Register",
            "logout": "Logout",
            "refunds": "Refunds",
            "user-refund-request": "Refund Request",
            "refund-policy": "Refund Policy",
            "sales-terms": "Sales Terms",
            "service-booking-terms": "Service Booking Terms",
        }
        display_name = display_name_map.get(
            part, part.replace("-", " ").replace("_", " ").title()
        )

        # For the last part, it's the current page, so it's not a link
        if i == len(path_parts) - 1:
            breadcrumbs_list.append(
                {
                    "name": display_name,
                    "url": None,  # Last item is not a link
                }
            )
        else:
            breadcrumbs_list.append({"name": display_name, "url": current_path})

    # Generate JSON-LD for Schema.org
    json_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [],
    }

    for i, breadcrumb in enumerate(breadcrumbs_list):
        if breadcrumb["url"]:  # Only include linked items in JSON-LD
            json_ld["itemListElement"].append(
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": breadcrumb["name"],
                    "item": request.build_absolute_uri(breadcrumb["url"]),
                }
            )
        else:  # For the last item (current page), include it without an item URL
            json_ld["itemListElement"].append(
                {"@type": "ListItem", "position": i + 1, "name": breadcrumb["name"]}
            )

    return {
        "breadcrumbs": breadcrumbs_list,
        "json_ld_breadcrumbs": json.dumps(json_ld, indent=2),
    }
