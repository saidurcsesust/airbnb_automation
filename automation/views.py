from django.shortcuts import render, get_object_or_404
from .models import TestRun


def dashboard(request):
    runs = TestRun.objects.prefetch_related("test_cases").all()
    context = {
        "runs": runs,
        "total": runs.count(),
        "passed": runs.filter(status="passed").count(),
        "failed": runs.filter(status="failed").count(),
    }
    return render(request, "automation/dashboard.html", context)


def run_detail(request, run_id):
    run = get_object_or_404(
        TestRun.objects.prefetch_related(
            "test_cases", "suggestions", "listings",
            "network_logs", "console_logs",
        ),
        pk=run_id,
    )
    return render(request, "automation/run_detail.html", {"run": run})
