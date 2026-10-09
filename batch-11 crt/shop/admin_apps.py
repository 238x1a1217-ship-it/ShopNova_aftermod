from django.contrib.admin.apps import AdminConfig


class GCommerceAdminConfig(AdminConfig):
    default_site = "shop.admin_site.GCommerceAdminSite"
