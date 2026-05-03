from django.urls import path
from .views import RateCalculatorView

app_name = "shipping_api"

urlpatterns = [
    path("rate-calculator/", RateCalculatorView.as_view(), name="rate-calculator"),
]