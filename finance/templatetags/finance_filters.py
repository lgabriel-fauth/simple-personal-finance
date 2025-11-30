from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter(name="currency")
def currency(value):
    try:
        if value is None:
            return "BRL 0.00"
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        q = value.quantize(Decimal("0.01"))
        # Format with thousands separator and dot as decimal separator (international style)
        s = f"{q:,.2f}"
        return f"BRL {s}"
    except (InvalidOperation, ValueError, TypeError):
        return "BRL 0.00"
