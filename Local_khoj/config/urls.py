"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from accounts import views as accounts_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import ProductSitemap, StoreSitemap


urlpatterns = [
    path('admin/', admin.site.urls),
     # Django built-in auth
    path("accounts/", include("django.contrib.auth.urls")),
    # Registration (simple view)
    path('register/', accounts_views.register, name='register'),
    # User profile and account pages
    path('user/', include('accounts.urls')),
    path('vendor/', include('vendor_panel.urls')),
    path("stores/", include("stores.urls")),
    path("cart/", include("cart.urls")),
    path("products/", include("products.urls")),
    path("orders/", include("orders.urls")),
    path("admin-panel/", include("admin_panel.urls")),

    path("", include("core.urls")),

    path("sitemap.xml", sitemap, {"sitemaps": {"products": ProductSitemap, "stores": StoreSitemap}}, name="sitemap"),



]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
