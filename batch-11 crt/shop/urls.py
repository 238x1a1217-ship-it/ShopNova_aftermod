from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("category/<int:category_id>/", views.category_products, name="category_products"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/increase/<int:product_id>/", views.cart_increase, name="cart_increase"),
    path("cart/decrease/<int:product_id>/", views.cart_decrease, name="cart_decrease"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/success/<int:pk>/", views.order_success, name="order_success"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("account/", views.profile, name="profile"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="login.html", redirect_authenticated_user=True),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
