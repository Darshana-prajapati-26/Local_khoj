from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Sum, Count
from accounts.models import User
from stores.models import Store, CategoryRequest
from products.models import Product
from services.models import Service
from orders.models import Order, Payment


def _is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff or getattr(user, "is_admin", lambda: False)())


@login_required
@user_passes_test(_is_admin)
def dashboard(request):
    total_users = User.objects.count()
    vendors = User.objects.filter(user_type="vendor").count()
    customers = User.objects.filter(user_type="customer").count()
    stores_count = Store.objects.count()
    verified_stores = Store.objects.filter(is_verified=True).count()
    active_stores = Store.objects.filter(is_active=True).count()
    products_count = Product.objects.count()
    services_count = Service.objects.count()
    orders_count = Order.objects.count()
    revenue = Payment.objects.filter(status__in=["completed", "success"]).aggregate(total=Sum("amount"))["total"] or 0
    recent_orders = Order.objects.order_by("-created_at")[:10]
    pending_categories = CategoryRequest.objects.filter(is_approved=False).order_by("-created_at")[:10]
    top_stores = Store.objects.order_by("-rating", "-total_reviews")[:10]
    by_status = list(Order.objects.values("status").annotate(c=Count("id")).order_by())
    ctx = {
        "total_users": total_users,
        "vendors": vendors,
        "customers": customers,
        "stores_count": stores_count,
        "verified_stores": verified_stores,
        "active_stores": active_stores,
        "products_count": products_count,
        "services_count": services_count,
        "orders_count": orders_count,
        "revenue": revenue,
        "recent_orders": recent_orders,
        "pending_categories": pending_categories,
        "top_stores": top_stores,
        "by_status": by_status,
    }
    return render(request, "admin_panel/dashboard.html", ctx)
