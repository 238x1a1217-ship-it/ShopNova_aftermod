from django.urls import path

from . import dashboard_views


app_name = "dashboard"

urlpatterns = [
    path("", dashboard_views.dashboard_home, name="home"),
    path("products/", dashboard_views.product_list, name="products"),
    path("products/add/", dashboard_views.product_create, name="product_add"),
    path("products/<int:pk>/edit/", dashboard_views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", dashboard_views.product_delete, name="product_delete"),
    path("categories/", dashboard_views.category_list, name="categories"),
    path("categories/add/", dashboard_views.category_create, name="category_add"),
    path("categories/<int:pk>/edit/", dashboard_views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", dashboard_views.category_delete, name="category_delete"),
    path("orders/", dashboard_views.order_list, name="orders"),
    path("orders/<int:pk>/status/", dashboard_views.order_status_update, name="order_status"),
    path("customers/", dashboard_views.customer_list, name="customers"),
    path("customers/<int:pk>/", dashboard_views.customer_detail, name="customer_detail"),
    path("inventory/", dashboard_views.inventory_list, name="inventory"),
    path("inventory/<int:pk>/", dashboard_views.inventory_update, name="inventory_update"),
]
