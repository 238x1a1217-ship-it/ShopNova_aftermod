from decimal import Decimal

from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _


class GCommerceAdminSite(AdminSite):
    site_header = _("G-Commerce Administration")
    site_title = _("G-Commerce")
    index_title = _("Store overview")
    index_template = "admin/gcommerce_index.html"

    def each_context(self, request):
        from .models import Product

        context = super().each_context(request)
        if self._registry[Product].has_view_or_change_permission(request):
            context["gcommerce_low_stock_count"] = Product.objects.filter(stock__lte=5).count()
        else:
            context["gcommerce_low_stock_count"] = 0
        return context

    def index(self, request, extra_context=None):
        from .models import Category, Order, Product

        orders = Order.objects.all()
        revenue = orders.exclude(status=Order.Status.CANCELLED).aggregate(total=Sum("total"))["total"]
        dashboard_context = {
            "gcommerce_product_count": Product.objects.count(),
            "gcommerce_category_count": Category.objects.count(),
            "gcommerce_order_count": orders.count(),
            "gcommerce_revenue": revenue or Decimal("0.00"),
            "gcommerce_low_stock_products": Product.objects.filter(stock__lte=5)
            .select_related("category")
            .order_by("stock", "name")[:6],
            "gcommerce_recent_orders": orders.select_related("user").order_by("-created_at", "-pk")[:6],
        }
        dashboard_context.update(extra_context or {})
        return super().index(request, extra_context=dashboard_context)

    def get_urls(self):
        custom_urls = [
            path(
                "inventory/",
                self.admin_view(self.inventory_view),
                name="inventory",
            ),
        ]
        return custom_urls + super().get_urls()

    def inventory_view(self, request):
        from .models import Product

        if not self._registry[Product].has_view_or_change_permission(request):
            raise PermissionDenied
        return redirect(f"{reverse('admin:shop_product_changelist')}?stock_status=low")
