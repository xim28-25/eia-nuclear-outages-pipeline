
from django.urls import path
from . import views

"""
Módulo urls — define las rutas URL disponibles en la API nuclear.
Mapea cada endpoint HTTP a su vista correspondiente en views.py.
Las tres rutas disponibles son:
  /api/data — consulta datos de salidas nucleares con filtros y paginación.
  /api/refresh — dispara la actualización completa de datos desde la EIA.
  /api/analytics — retorna el último análisis calculado por el pipeline.
"""

urlpatterns = [
    path("data",      views.data,      name="data"),
    path("refresh",   views.refresh,   name="refresh"),
    path("analytics", views.analytics, name="analytics"),
]