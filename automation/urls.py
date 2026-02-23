from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("run/<int:run_id>/", views.run_detail, name="run_detail"),
]
