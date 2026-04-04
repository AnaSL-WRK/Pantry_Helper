from datetime import timedelta

from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .utils import user_has_role, get_user_role
from .forms import FoodForm, IngredientForm
from .models import Food, Ingredient, Recipe


def _get_membership(user):
    if hasattr(user, 'household_member'):
        return user.household_member
    return None


def _get_available_foods_for_household(household):
    return Food.objects.select_related('ingredient').filter(
        household=household,
        quantity__gte=1
    )


def _build_recipe_suggestions(household, limit=None):
    today = timezone.localdate()
    expiring_limit = today + timedelta(days=7)

    available_foods = _get_available_foods_for_household(household)

    available_ingredient_ids = set()
    expiring_ingredient_ids = set()

    for food in available_foods:
        available_ingredient_ids.add(food.ingredient_id)

        if food.expiry_date and today <= food.expiry_date <= expiring_limit:
            expiring_ingredient_ids.add(food.ingredient_id)

    recipes = Recipe.objects.filter(
        is_preloaded=True,
        household__isnull=True
    ).prefetch_related(
        'recipe_ingredients__ingredient'
    ).order_by('name')

    suggestions = []

    for recipe in recipes:
        recipe_ingredients = list(recipe.recipe_ingredients.all())

        if not recipe_ingredients:
            continue

        total_count = len(recipe_ingredients)
        matched_count = 0
        expiring_match_count = 0
        missing_ingredients = []
        expiring_ingredients = []

        for recipe_ingredient in recipe_ingredients:
            ingredient_id = recipe_ingredient.ingredient_id
            ingredient_name = recipe_ingredient.ingredient.name

            if ingredient_id in available_ingredient_ids:
                matched_count += 1

                if ingredient_id in expiring_ingredient_ids:
                    expiring_match_count += 1
                    expiring_ingredients.append(ingredient_name)
            else:
                missing_ingredients.append(ingredient_name)

        if matched_count == 0:
            continue

        missing_count = total_count - matched_count

        suggestions.append({
            'recipe': recipe,
            'total_count': total_count,
            'matched_count': matched_count,
            'missing_count': missing_count,
            'missing_ingredients': missing_ingredients[:5],
            'expiring_match_count': expiring_match_count,
            'expiring_ingredients': expiring_ingredients[:5],
            'can_make_now': missing_count == 0,
            'almost_make_now': missing_count <= 2,
        })

    suggestions.sort(
        key=lambda item: (
            -item['expiring_match_count'],   # prioritize expiring foods first
            item['missing_count'],           # then recipes missing fewer ingredients
            -item['matched_count'],          # then recipes matching more ingredients
            item['recipe'].name.lower(),
        )
    )

    if limit is not None:
        suggestions = suggestions[:limit]

    return suggestions


def home(request):
    return render(request, 'app/home.html')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    membership = None
    role = get_user_role(request.user)
    foods = []
    expiring_foods = []
    expired_foods = []
    recipe_suggestions = []

    if hasattr(request.user, 'household_member'):
        membership = request.user.household_member
        today = timezone.localdate()
        expiring_limit = today + timedelta(days=7)

        foods = Food.objects.filter(
            household=membership.household,
            quantity__gte=1
        ).select_related('ingredient').order_by('expiry_date', 'ingredient__name')[:5]

        expiring_foods = Food.objects.filter(
            household=membership.household,
            quantity__gte=1,
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=expiring_limit
        ).select_related('ingredient').order_by('expiry_date', 'ingredient__name')[:5]

        expired_foods = Food.objects.filter(
            household=membership.household,
            quantity__gte=1,
            expiry_date__isnull=False,
            expiry_date__lt=today
        ).select_related('ingredient').order_by('expiry_date', 'ingredient__name')[:5]

        recipe_suggestions = _build_recipe_suggestions(
            membership.household,
            limit=5
        )

    tparams = {
        'membership': membership,
        'role': role,
        'foods': foods,
        'expiring_foods': expiring_foods,
        'expired_foods': expired_foods,
        'recipe_suggestions': recipe_suggestions,
    }

    return render(request, 'app/dashboard.html', tparams)


#all foods (food list)
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
    ).select_related('ingredient').order_by('expiry_date', 'ingredient__name')

    tparams = {
        'foods': foods,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/foodlist.html', tparams)


#create food item
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


#create ingredient
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


#list of recipes (recipe list)
def recipe_list(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    membership = request.user.household_member if hasattr(request.user, 'household_member') else None
    role = get_user_role(request.user)

    recipes = Recipe.objects.filter(
        is_preloaded=True,
        household__isnull=True
    ).order_by('name')

    tparams = {
        'recipes': recipes,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/recipes/recipelist.html', tparams)


#each recipe detail page (recipe detail)
def recipe_detail(request, recipe_id):
    if not request.user.is_authenticated:
        return redirect('/login/')

    membership = request.user.household_member if hasattr(request.user, 'household_member') else None
    role = get_user_role(request.user)

    recipe = get_object_or_404(
        Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient',
            'steps'
        ),
        pk=recipe_id
    )

    available_ingredient_ids = set()
    expiring_ingredient_ids = set()

    if membership:
        today = timezone.localdate()
        expiring_limit = today + timedelta(days=7)

        available_foods = Food.objects.filter(
            household=membership.household,
            quantity__gte=1
        )

        for food in available_foods:
            available_ingredient_ids.add(food.ingredient_id)

            if food.expiry_date and today <= food.expiry_date <= expiring_limit:
                expiring_ingredient_ids.add(food.ingredient_id)

    recipe_ingredients = list(recipe.recipe_ingredients.all())
    available_count = 0
    expiring_match_count = 0

    for recipe_ingredient in recipe_ingredients:
        recipe_ingredient.is_available = recipe_ingredient.ingredient_id in available_ingredient_ids
        recipe_ingredient.is_expiring_soon = recipe_ingredient.ingredient_id in expiring_ingredient_ids

        if recipe_ingredient.is_available:
            available_count += 1

        if recipe_ingredient.is_expiring_soon:
            expiring_match_count += 1

    total_ingredients = len(recipe_ingredients)
    missing_count = total_ingredients - available_count

    tparams = {
        'recipe': recipe,
        'recipe_ingredients': recipe_ingredients,
        'steps': recipe.steps.all(),
        'available_count': available_count,
        'missing_count': missing_count,
        'expiring_match_count': expiring_match_count,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/recipes/recipedetail.html', tparams)


#suggested recipes based on available ingredients
#prioritizes recipes that use expiring soon foods
def suggested_recipes(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not hasattr(request.user, 'household_member'):
        return redirect('/dashboard/')

    membership = request.user.household_member
    role = get_user_role(request.user)

    suggestions = _build_recipe_suggestions(membership.household, limit=30)

    tparams = {
        'suggestions': suggestions,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/recipes/suggestedrecipes.html', tparams)