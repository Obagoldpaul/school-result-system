from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    return render(request, "marketing/home.html")


def request_demo(request):
    return render(request, "marketing/request_demo.html")

def about(request):
    return render(request, "marketing/about.html")

def robots_txt(request):
    content = """User-agent: *
Allow: /

Sitemap: https://www.paulschoolhub.com.ng/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.paulschoolhub.com.ng/</loc>
    </url>
    <url>
        <loc>https://www.paulschoolhub.com.ng/about/</loc>
    </url>
    <url>
        <loc>https://www.paulschoolhub.com.ng/request-demo/</loc>
    </url>
</urlset>
"""
    return HttpResponse(content, content_type="application/xml")