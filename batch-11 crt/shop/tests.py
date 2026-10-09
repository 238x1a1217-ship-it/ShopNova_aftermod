from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, Order, OrderItem, Product


class ShopTestDataMixin:
    def setUp(self):
        self.category = Category.objects.create(name="Books")
        self.product = Product.objects.create(
            name="Field Notes",
            description="A useful notebook",
            price=Decimal("12.50"),
            stock=5,
            category=self.category,
        )
        self.user = User.objects.create_user(username="shopper", password="strong-password-123")


class ProductTests(ShopTestDataMixin, TestCase):
    def test_product_has_category_and_decimal_price(self):
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.category.products.get(), self.product)
        self.assertIsInstance(self.product.price, Decimal)
        self.assertEqual(str(self.product), "Field Notes")

    def test_list_search_category_and_sort(self):
        Product.objects.create(name="Another book", price="8.00", stock=1, category=self.category)
        response = self.client.get(reverse("product_list"), {"q": "field", "sort": "price_desc"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Field Notes")
        self.assertNotContains(response, "Another book")

        response = self.client.get(reverse("category_products", args=[self.category.pk]))
        self.assertEqual(len(response.context["products"]), 2)


class CartTests(ShopTestDataMixin, TestCase):
    def add_to_cart(self, quantity=1):
        return self.client.post(
            reverse("cart_add", args=[self.product.pk]),
            {"quantity": quantity},
        )

    def test_anonymous_user_can_add_product_and_badge_shows_quantity(self):
        response = self.add_to_cart(2)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("cart"))
        self.assertEqual(response.context["cart_item_count"], 2)
        self.assertEqual(response.context["items"][0]["quantity"], 2)

    def test_add_rejects_quantity_over_stock(self):
        self.add_to_cart(6)
        self.assertEqual(self.client.session.get("cart", {}), {})
        response = self.client.get(reverse("cart"))
        self.assertContains(response, "Your cart is empty")

    def test_increase_decrease_remove_and_clear(self):
        self.add_to_cart(1)
        self.client.post(reverse("cart_increase", args=[self.product.pk]))
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 2)
        self.client.post(reverse("cart_decrease", args=[self.product.pk]))
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 1)
        self.client.post(reverse("cart_remove", args=[self.product.pk]))
        self.assertEqual(self.client.session["cart"], {})
        self.add_to_cart()
        self.client.post(reverse("cart_clear"))
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_mutation_requires_post(self):
        response = self.client.get(reverse("cart_add", args=[self.product.pk]))
        self.assertEqual(response.status_code, 400)


class CheckoutTests(ShopTestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def add_product_to_cart(self, quantity):
        return self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": quantity})

    def test_checkout_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_order_snapshots_price_calculates_total_and_reduces_stock(self):
        self.add_product_to_cart(3)
        checkout_page = self.client.get(reverse("checkout"))
        self.assertEqual(checkout_page.status_code, 200)
        self.assertContains(checkout_page, "Cash on delivery")
        response = self.client.post(reverse("checkout"))
        order = Order.objects.get()
        self.assertRedirects(response, reverse("order_success", args=[order.pk]))
        self.assertContains(self.client.get(response.url), "Thank you for your order.")
        item = OrderItem.objects.get(order=order)
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total, Decimal("37.50"))
        self.assertEqual(item.price, Decimal("12.50"))
        self.assertEqual(item.subtotal, Decimal("37.50"))
        self.assertEqual(item.quantity, 3)
        self.assertEqual(self.product.__class__.objects.get(pk=self.product.pk).stock, 2)
        self.assertEqual(self.client.session["cart"], {})

        self.product.price = Decimal("20.00")
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("12.50"))

    def test_checkout_rejects_insufficient_stock_without_creating_order(self):
        self.add_product_to_cart(4)
        Product.objects.filter(pk=self.product.pk).update(stock=3)
        response = self.client.post(reverse("checkout"))
        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.exists())
        self.assertEqual(Product.objects.get(pk=self.product.pk).stock, 3)

    def test_order_history_and_detail_are_private_to_owner(self):
        order = Order.objects.create(user=self.user, total=Decimal("12.50"))
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=Decimal("12.50"),
            subtotal=Decimal("12.50"),
        )
        other_user = User.objects.create_user(username="someone-else", password="strong-password-123")
        self.client.force_login(other_user)
        self.assertEqual(self.client.get(reverse("order_detail", args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("order_history")).context["orders"].count(), 0)
        self.client.force_login(self.user)
        response = self.client.get(reverse("order_detail", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Field Notes")

    def test_profile_requires_login_and_displays_account(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("profile")).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, self.user.username)

    def test_empty_cart_cannot_checkout(self):
        response = self.client.post(reverse("checkout"))
        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.exists())


class AuthenticationTests(ShopTestDataMixin, TestCase):
    def test_registration_creates_user_with_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-shopper",
                "email": "shopper@example.com",
                "password1": "SecurePass!932",
                "password2": "SecurePass!932",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="new-shopper", email="shopper@example.com").exists())
        self.assertIn("_auth_user_id", self.client.session)


class OrderAdminTests(ShopTestDataMixin, TestCase):
    def test_order_change_page_renders_order_items(self):
        order = Order.objects.create(user=self.user, total=Decimal("12.50"))
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=Decimal("12.50"),
            subtotal=Decimal("12.50"),
        )
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin-password-123",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:shop_order_change", args=[order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Field Notes")
        self.assertEqual(str(item), "1 × Field Notes")


class DashboardTests(ShopTestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.staff_user = User.objects.create_user(
            username="store-admin",
            password="admin-password-123",
            is_staff=True,
        )
        self.dashboard = reverse("dashboard:home")
        self.client.force_login(self.staff_user)

    def test_dashboard_requires_staff_access(self):
        self.client.logout()
        response = self.client.get(self.dashboard)
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.dashboard).status_code, 302)

    def test_dashboard_metrics_use_database_values_and_exclude_cancelled_revenue(self):
        Order.objects.create(user=self.user, total=Decimal("30.00"), status=Order.Status.DELIVERED)
        Order.objects.create(user=self.user, total=Decimal("20.00"), status=Order.Status.PENDING)
        Order.objects.create(user=self.user, total=Decimal("100.00"), status=Order.Status.CANCELLED)
        Product.objects.filter(pk=self.product.pk).update(stock=3)

        response = self.client.get(self.dashboard)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product_count"], 1)
        self.assertEqual(response.context["category_count"], 1)
        self.assertEqual(response.context["order_count"], 3)
        self.assertEqual(response.context["revenue"], Decimal("50.00"))
        self.assertEqual(response.context["low_stock_count"], 1)

    def test_product_list_search_and_product_create_update(self):
        response = self.client.get(reverse("dashboard:products"), {"q": "Field"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Field Notes")

        response = self.client.post(
            reverse("dashboard:product_add"),
            {
                "name": "Desk Lamp",
                "description": "A practical desk lamp",
                "price": "24.95",
                "stock": "8",
                "category": self.category.pk,
            },
        )
        self.assertRedirects(response, reverse("dashboard:products"))
        created = Product.objects.get(name="Desk Lamp")
        response = self.client.post(
            reverse("dashboard:product_edit", args=[created.pk]),
            {
                "name": "Reading Lamp",
                "description": "A practical desk lamp",
                "price": "29.95",
                "stock": "7",
                "category": self.category.pk,
            },
        )
        self.assertRedirects(response, reverse("dashboard:products"))
        created.refresh_from_db()
        self.assertEqual(created.name, "Reading Lamp")
        self.assertEqual(created.price, Decimal("29.95"))

    def test_category_management_refuses_delete_while_products_exist(self):
        response = self.client.post(
            reverse("dashboard:category_add"),
            {"name": "Stationery"},
        )
        self.assertRedirects(response, reverse("dashboard:categories"))
        new_category = Category.objects.get(name="Stationery")
        response = self.client.post(
            reverse("dashboard:category_edit", args=[new_category.pk]),
            {"name": "Office"},
        )
        self.assertRedirects(response, reverse("dashboard:categories"))
        new_category.refresh_from_db()
        self.assertEqual(new_category.name, "Office")

        response = self.client.post(reverse("dashboard:category_delete", args=[self.category.pk]))
        self.assertRedirects(response, reverse("dashboard:categories"))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_order_status_update_and_filter(self):
        order = Order.objects.create(user=self.user, total=Decimal("12.50"))
        response = self.client.post(
            reverse("dashboard:order_status", args=[order.pk]),
            {"status": Order.Status.SHIPPED},
        )
        self.assertRedirects(response, reverse("dashboard:orders"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

        response = self.client.get(reverse("dashboard:orders"), {"status": Order.Status.SHIPPED})
        self.assertEqual(list(response.context["page_obj"].object_list), [order])

    def test_inventory_filter_and_update_reject_negative_stock(self):
        response = self.client.post(
            reverse("dashboard:inventory_update", args=[self.product.pk]),
            {"stock": "0"},
        )
        self.assertRedirects(response, reverse("dashboard:inventory"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

        response = self.client.post(
            reverse("dashboard:inventory_update", args=[self.product.pk]),
            {"stock": "-1"},
        )
        self.assertRedirects(response, reverse("dashboard:inventory"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

        response = self.client.get(reverse("dashboard:inventory"), {"stock": "out"})
        self.assertEqual(list(response.context["page_obj"].object_list), [self.product])

    def test_dashboard_pages_render(self):
        order = Order.objects.create(user=self.user, total=Decimal("12.50"))
        routes = (
            reverse("dashboard:products"),
            reverse("dashboard:product_add"),
            reverse("dashboard:product_edit", args=[self.product.pk]),
            reverse("dashboard:categories"),
            reverse("dashboard:category_add"),
            reverse("dashboard:category_edit", args=[self.category.pk]),
            reverse("dashboard:orders"),
            reverse("dashboard:customers"),
            reverse("dashboard:customer_detail", args=[self.user.pk]),
            reverse("dashboard:inventory"),
        )
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_product_list_paginates_and_preserves_search_filter(self):
        Product.objects.bulk_create(
            [
                Product(
                    name=f"Dashboard Product {number}",
                    price=Decimal("5.00"),
                    stock=10,
                    category=self.category,
                )
                for number in range(13)
            ]
        )

        response = self.client.get(reverse("dashboard:products"), {"q": "Dashboard Product"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)
        self.assertContains(response, "page=2")

    def test_product_delete_is_post_only_and_preserves_ordered_products(self):
        order = Order.objects.create(user=self.user, total=Decimal("12.50"))
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=Decimal("12.50"),
            subtotal=Decimal("12.50"),
        )
        response = self.client.post(reverse("dashboard:product_delete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("dashboard:products"))
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(
            self.client.get(reverse("dashboard:product_delete", args=[self.product.pk])).status_code,
            405,
        )


class GCommerceAdminSiteTests(ShopTestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.superuser = User.objects.create_superuser(
            username="gcommerce-admin",
            email="admin@example.com",
            password="admin-password-123",
        )
        self.client.force_login(self.superuser)

    def test_default_admin_site_uses_gcommerce_dashboard_with_real_metrics(self):
        from .admin_site import GCommerceAdminSite

        self.assertIsInstance(admin.site, GCommerceAdminSite)
        Order.objects.create(user=self.user, total=Decimal("23.00"))
        Order.objects.create(user=self.user, total=Decimal("70.00"), status=Order.Status.CANCELLED)
        Product.objects.filter(pk=self.product.pk).update(stock=2)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "G-Commerce")
        self.assertContains(response, "Total products")
        self.assertContains(response, "₹23.00")
        self.assertContains(response, "2 left")
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Customers")

    def test_default_admin_management_pages_and_inventory_filter_work(self):
        order = Order.objects.create(user=self.user, total=Decimal("12.50"))
        routes = (
            reverse("admin:shop_product_changelist"),
            reverse("admin:shop_category_changelist"),
            reverse("admin:shop_order_changelist"),
            reverse("admin:auth_user_changelist"),
        )
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

        response = self.client.get(reverse("admin:inventory"))
        self.assertRedirects(
            response,
            f"{reverse('admin:shop_product_changelist')}?stock_status=low",
        )

        response = self.client.post(
            reverse("admin:shop_order_changelist"),
            {
                "form-INITIAL_FORMS": "1",
                "form-TOTAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(order.pk),
                "form-0-status": Order.Status.SHIPPED,
                "_save": "Save",
            },
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_staff_without_model_permissions_can_open_dashboard_but_not_inventory(self):
        staff_user = User.objects.create_user(
            username="limited-staff",
            password="staff-password-123",
            is_staff=True,
        )
        self.client.force_login(staff_user)
        Order.objects.create(user=self.user, total=Decimal("12.50"))
        dashboard_response = self.client.get(reverse("admin:index"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertNotContains(dashboard_response, "Total products")
        self.assertNotContains(dashboard_response, "Recent orders")
        self.assertNotContains(dashboard_response, "Stock alerts")
        self.assertNotContains(dashboard_response, self.user.username)
        response = self.client.get(reverse("admin:inventory"), follow=True)
        self.assertEqual(response.status_code, 403)
