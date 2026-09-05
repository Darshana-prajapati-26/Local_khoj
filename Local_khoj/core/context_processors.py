from stores.models import Store, City


def global_data(request):
    try:
        cities = list(City.objects.values_list("name", flat=True).distinct().order_by("name"))
    except Exception:
        cities = []
    selected_city = request.GET.get("city") or request.session.get("city") or ""

    user_store = None
    if request.user.is_authenticated:
        user_store = Store.objects.filter(vendor=request.user).first()

    return {
        "cities": cities,
        "selected_city": selected_city,
        "user_store": user_store,
    }
