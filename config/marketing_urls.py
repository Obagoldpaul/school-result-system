from django.urls import path
from marketing import views

urlpatterns = [
    path("", views.home, name="marketing_home"),
    path("about/", views.about, name="marketing_about"),
    path("request-demo/", views.request_demo, name="request_demo"),
    path("robots.txt", views.robots_txt, name="marketing_robots"),
    path("sitemap.xml", views.sitemap_xml, name="marketing_sitemap"),
]