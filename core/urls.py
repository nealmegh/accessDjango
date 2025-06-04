from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('report/', views.report, name='report'),
    path('preview/', views.preview_page, name='preview'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('guidelines/', views.guidelines, name='guidelines'),
    path('export/csv/', views.export_csv, name='export_csv'),
    # path('export/pdf/', views.export_pdf, name='export_pdf'),
    path("render/", views.render_dom, name="render_dom"),
]