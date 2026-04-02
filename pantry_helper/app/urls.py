#urls from app

from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('foods/', views.food_list, name='food_list'),
    path('foods/new/', views.food_new, name='food_new'),
    path('ingredients/new/', views.ingredient_new, name='ingredient_new'),
]