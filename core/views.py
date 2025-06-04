from django.http import HttpResponse, HttpResponseNotFound
from .models import Rule
from django.shortcuts import render, redirect
from .scanner import run_accessibility_scan, run_accessibility_scan_with_dom_capture, fetch_html
# from .browser_capture import capture_screenshot
# from django.utils.html import escape
# import requests
# from bs4 import BeautifulSoup
from django.views.decorators.clickjacking import xframe_options_exempt
import csv
from django.template.loader import render_to_string
from .models import ScanHistory
import urllib3
import os
import uuid
from django.conf import settings
# from weasyprint import HTML
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SNAPSHOT_DIR = os.path.join(settings.BASE_DIR, 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

@xframe_options_exempt
def preview_page(request):
    url = request.GET.get("url")
    if not url:
        return HttpResponse("No URL provided.", status=400)

    try:
        # Run full JS-rendered scan
        report_data, final_html, scan_id = run_accessibility_scan_with_dom_capture(url)

        # Save snapshot
        file_path = os.path.join(SNAPSHOT_DIR, f"{scan_id}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_html)

        return render(request, "core/report.html", {
            "report": report_data,
            "url": url,
            "scan_id": scan_id
        })

    except Exception as e:
        return HttpResponse(f"Error during rendering: {e}", status=500)

def render_dom(request):
    scan_id = request.GET.get("uid")
    file_path = os.path.join(SNAPSHOT_DIR, f"{scan_id}.html")

    if not os.path.exists(file_path):
        return HttpResponseNotFound("Rendered snapshot not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    response = HttpResponse(html, content_type="text/html")
    response["X-Frame-Options"] = "ALLOWALL"
    return response

def report(request):
    url = request.GET.get("url")
    if not url:
        return redirect("home")

    report_data, final_html, scan_id = run_accessibility_scan_with_dom_capture(url)

    # Save the rendered HTML for iframe use
    file_path = os.path.join(SNAPSHOT_DIR, f"{scan_id}.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    ScanHistory.objects.create(
        url=url,
        summary=report_data.get('summary', {})
    )

    return render(request, 'core/report.html', {
        'report': report_data,
        'url': url,
        'scan_id': scan_id
    })

def home(request):
    return render(request, 'core/home.html')

def export_csv(request):
    url = request.GET.get("url")
    report_data, _, _ = run_accessibility_scan_with_dom_capture(url)
    results = report_data.get("details", [])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="accessibility_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Type', 'Element', 'Suggestion'])
    for item in results:
        writer.writerow([item.get('type', item.get('id')), item.get('element', ''), item.get('suggestion', item.get('help', ''))])
    return response

# def export_pdf(request):
#     url = request.GET.get("url")
#     report_data, _, _ = run_accessibility_scan_with_dom_capture(url)
#
#     html_string = render_to_string('core/pdf_template.html', {'report': report_data, 'url': url})
#     pdf_file = HTML(string=html_string).write_pdf()
#
#     response = HttpResponse(pdf_file, content_type='application/pdf')
#     response['Content-Disposition'] = 'attachment; filename="accessibility_report.pdf"'
#     return response

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

def guidelines(request):
    rules = Rule.objects.all()
    return render(request, 'core/guidelines.html', {'rules': rules})