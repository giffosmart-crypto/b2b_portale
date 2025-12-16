from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("product/<slug:slug>/availability/", views.product_availability, name="product_availability"),
    path("product/<slug:slug>/rate/", views.add_rating, name="add_rating"),
]
