from django.urls import path, include
from django.http import JsonResponse

def root(request):
    return JsonResponse({"message": "EIA Nuclear Outages API", "endpoints": ["/api/data", "/api/refresh", "/api/analytics"]})

urlpatterns = [
    path("", root),           
    path("api/", include("outages.urls")),
]