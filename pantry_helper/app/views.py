from django.shortcuts import redirect, render
from django.urls import reverse

from .utils import user_has_role, get_user_role
from .forms import FoodForm, IngredientForm
from .models import Food, Ingredient


def home(request):
    return render(request, 'app/home.html')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    membership = None
    role = get_user_role(request.user)
    foods = []

    if hasattr(request.user, 'household_member'):
        membership = request.user.household_member
        foods = Food.objects.filter(
            household=membership.household,
            quantity__gte=1
        ).order_by('expiry_date', 'ingredient__name')[:5]

    tparams = {
        'membership': membership,
        'role': role,
        'foods': foods,
    }

    return render(request, 'app/dashboard.html', tparams)


def food_list(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not hasattr(request.user, 'household_member'):
        return redirect('/dashboard/')

    membership = request.user.household_member
    role = get_user_role(request.user)

    foods = Food.objects.filter(
        household=membership.household,
        quantity__gte=1
    ).order_by('expiry_date', 'ingredient__name')

    tparams = {
        'foods': foods,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/foodlist.html', tparams)


def food_new(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not (user_has_role(request.user, 'HouseholdAdmin') or user_has_role(request.user, 'InventoryManager')):
        return redirect('/dashboard/')

    if not hasattr(request.user, 'household_member'):
        return redirect('/dashboard/')

    membership = request.user.household_member
    role = get_user_role(request.user)

    initial_data = {}
    ingredient_id = request.GET.get('ingredient')

    if ingredient_id and Ingredient.objects.filter(pk=ingredient_id).exists():
        initial_data['ingredient'] = ingredient_id

    if request.method == 'POST':
        form = FoodForm(request.POST)
        if form.is_valid():
            food = form.save(commit=False)
            food.household = membership.household
            food.added_by = request.user
            food.save()
            return redirect('app:food_list')
    else:
        form = FoodForm(initial=initial_data)

    add_ingredient_url = f"{reverse('app:ingredient_new')}?next={reverse('app:food_new')}"

    tparams = {
        'form': form,
        'role': role,
        'add_ingredient_url': add_ingredient_url,
    }

    return render(request, 'app/foodform.html', tparams)


def ingredient_new(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not (user_has_role(request.user, 'HouseholdAdmin') or user_has_role(request.user, 'InventoryManager')):
        return redirect('/dashboard/')

    next_url = request.GET.get('next') or request.POST.get('next') or reverse('app:food_new')

    if request.method == 'POST':
        form = IngredientForm(request.POST)

        if form.is_valid():
            ingredient = form.save()
            return redirect(f'{next_url}?ingredient={ingredient.pk}')
    else:
        form = IngredientForm()

    tparams = {
        'form': form,
        'next_url': next_url,
    }

    return render(request, 'app/ingredientform.html', tparams)