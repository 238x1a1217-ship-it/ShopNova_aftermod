from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .cart import SESSION_CART_KEY, get_cart, get_cart_items
from .forms import RegistrationForm
from .models import Category, Order, OrderItem, Product


def home(request):
    categories = Category.objects.all()[:6]
    featured_products = Product.objects.select_related("category").order_by("-created_at")[:8]
    return render(
        request,
        "home.html",
        {"categories": categories, "featured_products": featured_products},
    )


def product_list(request, products=None, selected_category=None):
    categories = Category.objects.all()
    if products is None:
        products = Product.objects.select_related("category").all()
        category_id = request.GET.get("category")
        if category_id:
            products = products.filter(category_id=category_id)
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(name__icontains=query)
    sort = request.GET.get("sort", "")
    if sort == "price_asc":
        products = products.order_by("price", "name")
    elif sort == "price_desc":
        products = products.order_by("-price", "name")
    return render(
        request,
        "product_list.html",
        {
            "products": products,
            "categories": categories,
            "selected_category": selected_category,
            "query": query,
            "sort": sort,
        },
    )


def category_products(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    return product_list(
        request,
        products=Product.objects.select_related("category").filter(category=category),
        selected_category=category,
    )


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    return render(request, "product_detail.html", {"product": product})


def _get_post_quantity(request, default=1):
    raw_quantity = request.POST.get("quantity", str(default))
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


def cart_add(request, product_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Cart updates must use POST.")
    product = get_object_or_404(Product, pk=product_id)
    quantity = _get_post_quantity(request)
    if quantity is None:
        messages.error(request, "Please choose a valid quantity.")
        return redirect("product_detail", pk=product_id)
    cart = get_cart(request).copy()
    try:
        existing_quantity = int(cart.get(str(product_id), 0))
    except (TypeError, ValueError):
        existing_quantity = 0
    if product.stock == 0:
        messages.error(request, "This product is out of stock.")
    elif existing_quantity + quantity > product.stock:
        messages.error(request, f"Only {product.stock} available. Your cart already has {existing_quantity}.")
    else:
        cart[str(product_id)] = existing_quantity + quantity
        request.session[SESSION_CART_KEY] = cart
        messages.success(request, f"{product.name} added to your cart.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect("cart")


def cart_increase(request, product_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Cart updates must use POST.")
    product = get_object_or_404(Product, pk=product_id)
    cart = get_cart(request).copy()
    try:
        quantity = int(cart.get(str(product_id), 0))
    except (TypeError, ValueError):
        quantity = 0
    if quantity == 0:
        messages.error(request, "That product is not in your cart.")
    elif quantity >= product.stock:
        messages.error(request, f"Only {product.stock} available.")
    else:
        cart[str(product_id)] = quantity + 1
        request.session[SESSION_CART_KEY] = cart
    return redirect("cart")


def cart_decrease(request, product_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Cart updates must use POST.")
    cart = get_cart(request).copy()
    try:
        quantity = int(cart.get(str(product_id), 0))
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 1:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = quantity - 1
    request.session[SESSION_CART_KEY] = cart
    return redirect("cart")


def cart_remove(request, product_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Cart updates must use POST.")
    cart = get_cart(request).copy()
    cart.pop(str(product_id), None)
    request.session[SESSION_CART_KEY] = cart
    messages.success(request, "Product removed from your cart.")
    return redirect("cart")


def cart_clear(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Cart updates must use POST.")
    request.session[SESSION_CART_KEY] = {}
    messages.success(request, "Your cart has been cleared.")
    return redirect("cart")


def cart_detail(request):
    items, total = get_cart_items(request)
    return render(request, "cart.html", {"items": items, "total": total})


@login_required
def checkout(request):
    items, total = get_cart_items(request)
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("cart")
    unavailable = [item for item in items if not item["available"]]
    if unavailable:
        messages.error(request, "Please update your cart: one or more products no longer have enough stock.")
        return redirect("cart")

    if request.method == "POST":
        cart = get_cart(request)
        quantities = {}
        try:
            for raw_id, raw_quantity in cart.items():
                product_id, quantity = int(raw_id), int(raw_quantity)
                if product_id <= 0 or quantity <= 0:
                    raise ValueError
                quantities[product_id] = quantity
        except (TypeError, ValueError):
            messages.error(request, "Your cart contains invalid items. Please review it and try again.")
            return redirect("cart")

        with transaction.atomic():
            products = list(
                Product.objects.select_for_update()
                .filter(pk__in=quantities)
                .order_by("pk")
            )
            if len(products) != len(quantities):
                messages.error(request, "A product in your cart is no longer available.")
                return redirect("cart")
            insufficient = [
                product
                for product in products
                if quantities[product.pk] > product.stock
            ]
            if insufficient:
                messages.error(
                    request,
                    "Not enough stock available for: "
                    + ", ".join(f"{product.name} (only {product.stock} left)" for product in insufficient),
                )
                return redirect("cart")

            order_total = sum(
                (product.price * quantities[product.pk] for product in products),
                Decimal("0.00"),
            )
            order = Order.objects.create(user=request.user, total=order_total)
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=product,
                        quantity=quantities[product.pk],
                        price=product.price,
                        subtotal=product.price * quantities[product.pk],
                    )
                    for product in products
                ]
            )
            for product in products:
                product.stock -= quantities[product.pk]
                product.save(update_fields=["stock", "updated_at"])

        request.session[SESSION_CART_KEY] = {}
        messages.success(request, "Your order was placed successfully.")
        return redirect("order_success", pk=order.pk)

    return render(request, "checkout.html", {"items": items, "total": total})


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "order_success.html", {"order": order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, "order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        pk=pk,
        user=request.user,
    )
    return render(request, "order_detail.html", {"order": order})


@login_required
def profile(request):
    return render(request, "profile.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    next_url = request.POST.get("next") or request.GET.get("next", "")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account has been created.")
        if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
            return redirect(next_url)
        return redirect("home")
    return render(request, "register.html", {"form": form, "next": next_url})
