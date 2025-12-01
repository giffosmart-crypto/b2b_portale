from django.urls import path
from .views import HomeView

app_name = "cms"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]
