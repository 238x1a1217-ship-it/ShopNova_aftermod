def cart_summary(request):
    cart = request.session.get("cart", {})
    count = 0
    if isinstance(cart, dict):
        for quantity in cart.values():
            try:
                count += max(0, int(quantity))
            except (TypeError, ValueError):
                continue
    return {"cart_item_count": count}
