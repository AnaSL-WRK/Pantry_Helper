#urls from app

from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('categories/new/', views.category_new, name='category_new'),
    path('items/', views.item_list, name='item_list'),
    path('items/new/', views.item_new, name='item_new'),
]