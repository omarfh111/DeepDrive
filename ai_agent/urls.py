from django.urls import path
from . import views

app_name = "ai_agent"

urlpatterns = [
    path("deep-research/", views.deep_research_dashboard, name="deep_research_dashboard"),
    path(
        "research/download/<int:pk>/",
        views.download_research_html,
        name="download_research_html",
    ),
]
