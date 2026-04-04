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
    
    path('recipes/', views.recipe_list, name='recipe_list'),
    path('recipes/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipes/suggested/', views.suggested_recipes, name='suggested_recipes'),
]