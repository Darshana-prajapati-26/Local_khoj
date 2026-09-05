from django import template
from django.utils.text import slugify as dj_slugify

register = template.Library()


@register.filter
def slugify(value):
    try:
        return dj_slugify(value or "")
    except Exception:
        return ""

@register.filter
def eq(value, other):
    try:
        return str(value or "") == str(other or "")
    except Exception:
        return False

@register.filter
def category_icon(slug):
    icons = {
        'shops': 'bi-shop',
        'restaurants': 'bi-egg-fried',
        'services': 'bi-tools',
        'hospitals': 'bi-plus-circle',
        'education': 'bi-book',
        'beauty': 'bi-scissors',
        'salon': 'bi-scissors',
        'grocery': 'bi-cart',
        'pharmacy': 'bi-capsule',
        'electronics': 'bi-laptop',
        'fashion': 'bi-handbag',
        'automotive': 'bi-car-front',
        'real-estate': 'bi-house',
        'travel': 'bi-airplane',
        'entertainment': 'bi-controller',
        'banking': 'bi-bank',
        'fitness': 'bi-heart-pulse',
        'gym': 'bi-heart-pulse',
    }
    return icons.get(slug, 'bi-grid')

@register.filter
def category_color(slug):
    colors = {
        'shops': 'text-danger',
        'restaurants': 'text-warning',
        'services': 'text-primary',
        'hospitals': 'text-danger',
        'education': 'text-info',
        'beauty': 'text-pink', # CSS needs to support pink
        'salon': 'text-pink',
        'grocery': 'text-success',
        'pharmacy': 'text-danger',
        'electronics': 'text-secondary',
        'fashion': 'text-dark',
        'automotive': 'text-primary',
        'real-estate': 'text-info',
        'travel': 'text-warning',
        'entertainment': 'text-primary',
        'banking': 'text-success',
        'fitness': 'text-danger',
        'gym': 'text-danger',
    }
    return colors.get(slug, 'text-primary')

@register.filter
def star_range(value):
    try:
        return range(int(value or 0))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def empty_star_range(value):
    try:
        return range(5 - int(value or 0))
    except (ValueError, TypeError):
        return range(5)

@register.simple_tag
def get_cart_count(user):
    if not user.is_authenticated:
        return 0
    from cart.models import Cart
    cart = Cart.objects.filter(user=user).first()
    if cart:
        return sum(item.quantity for item in cart.items.all())
    return 0
