from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .dashboard_forms import (
    DashboardCategoryForm,
    DashboardProductForm,
    InventoryStockForm,
    OrderStatusForm,
)
from .models import Category, Order, Product


LOW_STOCK_THRESHOLD = 5
PAGE_SIZE = 12


def _paginate(request, queryset):
    paginator = Paginator(queryset, PAGE_SIZE)
    return paginator.get_page(request.GET.get("page"))


def _management_context(request, active, page_title, **kwargs):
    return {
        "active_nav": active,
        "page_title": page_title,
        "low_stock_nav_count": Product.objects.filter(stock__lte=LOW_STOCK_THRESHOLD).count(),
        **kwargs,
    }


@staff_member_required
def dashboard_home(request):
    orders = Order.objects.all()
    revenue = orders.exclude(status=Order.Status.CANCELLED).aggregate(total=Sum("total"))["total"]
    context = _management_context(
        request,
        "dashboard",
        "Dashboard",
        product_count=Product.objects.count(),
        category_count=Category.objects.count(),
        order_count=orders.count(),
        revenue=revenue or Decimal("0.00"),
        low_stock_count=Product.objects.filter(stock__lte=LOW_STOCK_THRESHOLD).count(),
        low_stock_products=Product.objects.filter(stock__lte=LOW_STOCK_THRESHOLD)
        .select_related("category")
        .order_by("stock", "name")[:6],
        recent_orders=orders.select_related("user").order_by("-created_at", "-id")[:6],
        low_stock_threshold=LOW_STOCK_THRESHOLD,
    )
    return render(request, "dashboard/home.html", context)


@staff_member_required
def product_list(request):
    products = Product.objects.select_related("category").all()
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    stock_filter = request.GET.get("stock", "")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))
    if stock_filter == "low":
        products = products.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD)
    elif stock_filter == "out":
        products = products.filter(stock=0)
    elif stock_filter == "available":
        products = products.filter(stock__gt=LOW_STOCK_THRESHOLD)
    context = _management_context(
        request,
        "products",
        "Products",
        page_obj=_paginate(request, products),
        categories=Category.objects.all(),
        query=query,
        selected_category=category_id,
        selected_stock=stock_filter,
        low_stock_threshold=LOW_STOCK_THRESHOLD,
    )
    return render(request, "dashboard/products.html", context)


@staff_member_required
def product_create(request):
    form = DashboardProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"{product.name} was added.")
        return redirect("dashboard:products")
    return render(
        request,
        "dashboard/product_form.html",
        _management_context(request, "products", "Add product", form=form, is_create=True),
    )


@staff_member_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = DashboardProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"{product.name} was updated.")
        return redirect("dashboard:products")
    return render(
        request,
        "dashboard/product_form.html",
        _management_context(request, "products", "Edit product", form=form, is_create=False, product=product),
    )


@staff_member_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    try:
        product.delete()
    except ProtectedError:
        messages.error(request, "This product cannot be deleted because it is referenced by an existing order.")
    else:
        messages.success(request, f"{name} was deleted.")
    return redirect("dashboard:products")


@staff_member_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    query = request.GET.get("q", "").strip()
    if query:
        categories = categories.filter(name__icontains=query)
    return render(
        request,
        "dashboard/categories.html",
        _management_context(request, "categories", "Categories", page_obj=_paginate(request, categories), query=query),
    )


@staff_member_required
def category_create(request):
    form = DashboardCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"{category.name} was added.")
        return redirect("dashboard:categories")
    return render(
        request,
        "dashboard/category_form.html",
        _management_context(request, "categories", "Add category", form=form),
    )


@staff_member_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = DashboardCategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"{category.name} was updated.")
        return redirect("dashboard:categories")
    return render(
        request,
        "dashboard/category_form.html",
        _management_context(request, "categories", "Edit category", form=form, category=category),
    )


@staff_member_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    name = category.name
    try:
        category.delete()
    except ProtectedError:
        messages.error(request, "This category still has products and cannot be deleted.")
    else:
        messages.success(request, f"{name} was deleted.")
    return redirect("dashboard:categories")


@staff_member_required
def order_list(request):
    orders = Order.objects.select_related("user").all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        order_query = Q(user__username__icontains=query) | Q(user__email__icontains=query)
        if query.isdigit():
            order_query |= Q(pk=int(query))
        orders = orders.filter(order_query)
    if status in Order.Status.values:
        orders = orders.filter(status=status)
    return render(
        request,
        "dashboard/orders.html",
        _management_context(
            request,
            "orders",
            "Orders",
            page_obj=_paginate(request, orders),
            query=query,
            selected_status=status,
            statuses=Order.Status.choices,
        ),
    )


@staff_member_required
@require_POST
def order_status_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = OrderStatusForm(request.POST, instance=order)
    if form.is_valid():
        form.save()
        messages.success(request, f"Order #{order.pk} status updated to {order.get_status_display()}.")
    else:
        messages.error(request, "Choose a valid order status.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard:orders")


@staff_member_required
def inventory_list(request):
    products = Product.objects.select_related("category").all()
    query = request.GET.get("q", "").strip()
    stock_filter = request.GET.get("stock", "")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    if stock_filter == "low":
        products = products.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD)
    elif stock_filter == "out":
        products = products.filter(stock=0)
    elif stock_filter == "available":
        products = products.filter(stock__gt=LOW_STOCK_THRESHOLD)
    return render(
        request,
        "dashboard/inventory.html",
        _management_context(
            request,
            "inventory",
            "Inventory",
            page_obj=_paginate(request, products),
            query=query,
            selected_stock=stock_filter,
            low_stock_threshold=LOW_STOCK_THRESHOLD,
        ),
    )


@staff_member_required
@require_POST
def inventory_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = InventoryStockForm(request.POST, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, f"Stock for {product.name} was updated.")
    else:
        messages.error(request, "Enter a valid non-negative stock quantity.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard:inventory")


@staff_member_required
def customer_list(request):
    User = get_user_model()
    customers = User.objects.filter(is_staff=False).annotate(
        order_count=Count("orders", distinct=True),
        total_spent=Sum("orders__total", filter=~Q(orders__status=Order.Status.CANCELLED)),
    ).order_by("username", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    return render(
        request,
        "dashboard/customers.html",
        _management_context(request, "customers", "Customers", page_obj=_paginate(request, customers), query=query),
    )


@staff_member_required
def customer_detail(request, pk):
    User = get_user_model()
    customer = get_object_or_404(User, pk=pk, is_staff=False)
    orders = Order.objects.filter(user=customer).order_by("-created_at", "-id")
    return render(
        request,
        "dashboard/customer_detail.html",
        _management_context(
            request,
            "customers",
            f"Customer: {customer.username}",
            customer=customer,
            page_obj=_paginate(request, orders),
        ),
    )
