from decimal import Decimal

from .models import Product


SESSION_CART_KEY = "cart"


def get_cart(request):
    cart = request.session.get(SESSION_CART_KEY, {})
    return cart if isinstance(cart, dict) else {}


def get_cart_items(request):
    cart = get_cart(request)
    product_ids = []
    quantities = {}
    for raw_id, raw_quantity in cart.items():
        try:
            product_id = int(raw_id)
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            continue
        if product_id > 0 and quantity > 0:
            product_ids.append(product_id)
            quantities[product_id] = quantity

    products = Product.objects.filter(pk__in=product_ids).select_related("category")
    items = []
    total = Decimal("0.00")
    for product in products:
        quantity = quantities[product.pk]
        subtotal = product.price * quantity
        total += subtotal
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal,
                "available": quantity <= product.stock,
            }
        )
    return items, total
