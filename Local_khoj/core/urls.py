from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("explore/", views.explore, name="explore"),
    path("offers/", views.offers, name="offers"),
    path("search/", views.search, name="search"),
    path("register/", views.register, name="register"),
    path("services/<int:pk>/", views.service_detail, name="service_detail"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/suggestions/", views.suggestions, name="suggestions"),
    path("api/suggestions/delete/", views.delete_search, name="suggestions_delete"),
    path("api/products/", views.api_products, name="api_products"),
    path("api/stores/", views.api_stores, name="api_stores"),
    path("api/notifications/", views.api_notifications, name="api_notifications"),
    path("api/notifications/delete/<int:notif_id>/", views.api_notification_delete, name="api_notification_delete"),

    path("chat/<slug:slug>/", views.chat_open, name="chat_open"),
    path("chat/send/<int:thread_id>/", views.chat_send, name="chat_send"),
    path("chat/poll/<int:thread_id>/", views.chat_poll, name="chat_poll"),
    path("lead/<slug:slug>/submit/", views.lead_submit, name="lead_submit"),
    path("click/<slug:slug>/<str:source>/", views.track_click, name="track_click"),
]
