from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name = "accounts"

urlpatterns = [
    # Dashboard cliente
    path("my/", views.my_dashboard, name="my_dashboard"),
    # ordini cliente
    path("my/orders/", views.my_orders_list, name="my_orders"),
    path("my/orders/<int:order_id>/", views.my_order_detail, name="my_order_detail"),
    path("my/orders/<int:order_id>/duplicate/", views.my_order_duplicate, name="my_order_duplicate"),

    # strutture cliente
    path("my/structures/", views.my_structures_list, name="my_structures_list"),
    path("my/structures/add/", views.my_structure_create, name="my_structure_create"),
    path("my/structures/<int:pk>/edit/", views.my_structure_edit, name="my_structure_edit"),
    path("my/structures/<int:pk>/delete/", views.my_structure_delete, name="my_structure_delete"),

    path("my/", views.my_dashboard, name="my_dashboard"),

    # REGISTRAZIONE
    path("register/", views.register, name="register"),

    # LOGIN
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),

    # LOGOUT
    path("logout/", views.logout_view, name="logout"),

    # PROFILO UTENTE (nuova route corretta)
    path("my/profile/", views.my_profile, name="my_profile"),

    # route legacy (compatibilità vecchi link)
    path("profile/", views.profile, name="profile"),

    # CAMBIO PASSWORD (frontend per tutti i ruoli)
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("accounts:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html"
        ),
        name="password_change_done",
    ),
]
