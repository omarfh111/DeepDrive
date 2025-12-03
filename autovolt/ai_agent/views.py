# ai_agent/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from .models import ResearchQuery
from ai_agent.services.deep_research_engine import deep_research, save_reports
import os
import logging

logger = logging.getLogger(__name__)


@login_required
def deep_research_dashboard(request):
    html_report = None
    query = ""

    # Always show last 20 queries of this user
    history = ResearchQuery.objects.filter(user=request.user).order_by("-created_at")[:20]

    if request.method == "POST":
        query = request.POST.get("query", "").strip()

        if query:
            try:
                markdown_report, html_report = deep_research(query)

                output_dir = r"D:/ai agent se"
                paths = save_reports(query, markdown_report, html_report, output_dir)

                ResearchQuery.objects.create(
                    user=request.user,
                    query=query,
                    markdown_path=paths.get("markdown"),
                    html_path=paths.get("html"),
                    pdf_path=paths.get("pdf"),
                )

                history = ResearchQuery.objects.filter(user=request.user).order_by(
                    "-created_at"
                )[:20]

            except Exception as e:
                logger.exception("Deep research failed")
                html_report = f"<p style='color:red;'>An error occurred: {str(e)}</p>"

    context = {
        "query": query,
        "html_report": html_report,
        "history": history,
    }
    return render(request, "ai_agent/research_dashboard.html", context)


@login_required
def download_research_html(request, pk: int):
    """
    Download the stored HTML report as an attachment.
    """
    rq = get_object_or_404(ResearchQuery, pk=pk, user=request.user)

    if not rq.html_path:
        raise Http404("No HTML file recorded for this research.")

    file_path = rq.html_path
    if not os.path.exists(file_path):
        raise Http404("HTML file not found on server.")

    filename = os.path.basename(file_path)

    # Read the file and return a normal HttpResponse (non-streaming)
    with open(file_path, "rb") as f:
        data = f.read()

    response = HttpResponse(data, content_type="text/html")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
