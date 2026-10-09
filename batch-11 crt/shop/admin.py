from django.contrib import admin

from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


class StockStatusFilter(admin.SimpleListFilter):
    title = "stock status"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("available", "In stock"),
            ("low", "Low stock (5 or fewer)"),
            ("out", "Out of stock"),
        )

    def queryset(self, request, queryset):
        if self.value() == "available":
            return queryset.filter(stock__gt=0)
        if self.value() == "low":
            return queryset.filter(stock__gt=0, stock__lte=5)
        if self.value() == "out":
            return queryset.filter(stock=0)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "created_at")
    list_editable = ("stock",)
    list_filter = ("category", StockStatusFilter, "created_at")
    search_fields = ("name",)
    list_select_related = ("category",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price", "subtotal")
    can_delete = False
    max_num = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "created_at")
    search_fields = ("=id", "user__username")
    list_select_related = ("user",)
    readonly_fields = ("user", "total", "created_at")
    inlines = (OrderItemInline,)
    list_per_page = 25
