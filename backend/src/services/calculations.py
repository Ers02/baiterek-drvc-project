def calculate_totals(quantity: float, price: float):
    if quantity is None or price is None:
        return None, None
    total = quantity * price
    return price, total