from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User


from .forms import FoodForm, IngredientForm, WasteForm, FoodQuantityForm, MemberRoleForm, HouseholdMemberCreateForm
from .models import Food, Ingredient, Recipe, WasteLog, HouseholdMember
from .utils import get_user_role, get_membership, assign_user_role


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
            -item['expiring_match_count'],
            item['missing_count'],
            -item['matched_count'],
            item['recipe'].name.lower(),
        )
    )

    if limit is not None:
        suggestions = suggestions[:limit]

    return suggestions


def home(request):
    return render(request, 'app/home.html')


@login_required
def dashboard(request):
    membership = get_membership(request.user)
    role = get_user_role(request.user)
    foods = []
    expiring_foods = []
    expired_foods = []
    recipe_suggestions = []
    waste_total = 0
    top_wasted_ingredients = []

    if membership:
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

        if request.user.has_perm('app.view_wastelog'):
            waste_total = (
                WasteLog.objects.filter(household=membership.household)
                .aggregate(total=Sum('quantity'))['total'] or 0
            )

            top_wasted_ingredients = (
                WasteLog.objects.filter(household=membership.household)
                .values('ingredient__name')
                .annotate(total_wasted=Sum('quantity'))
                .order_by('-total_wasted', 'ingredient__name')[:5]
            )

    tparams = {
        'membership': membership,
        'role': role,
        'foods': foods,
        'expiring_foods': expiring_foods,
        'expired_foods': expired_foods,
        'recipe_suggestions': recipe_suggestions,
        'waste_total': waste_total,
        'top_wasted_ingredients': top_wasted_ingredients,
    }

    return render(request, 'app/dashboard.html', tparams)


@login_required
@permission_required('app.view_food', raise_exception=True)
def food_list(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

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

    return render(request, 'app/food/foodlist.html', tparams)


@login_required
@permission_required('app.add_food', raise_exception=True)
def food_new(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

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
        'page_title': 'Add food',
        'submit_label': 'Save',
        'add_ingredient_url': add_ingredient_url,
    }

    return render(request, 'app/food/foodform.html', tparams)


@login_required
@permission_required('app.add_ingredient', raise_exception=True)
def ingredient_new(request):
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
        'page_title': 'Add ingredient',
        'next_url': next_url,
    }

    return render(request, 'app/ingredientform.html', tparams)


@login_required
@permission_required('app.view_recipe', raise_exception=True)
def recipe_list(request):
    membership = get_membership(request.user)
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


@login_required
@permission_required('app.view_recipe', raise_exception=True)
def recipe_detail(request, recipe_id):
    membership = get_membership(request.user)
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


@login_required
@permission_required('app.view_suggested_recipes', raise_exception=True)
def suggested_recipes(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    role = get_user_role(request.user)
    suggestions = _build_recipe_suggestions(membership.household, limit=30)

    tparams = {
        'suggestions': suggestions,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/recipes/suggestedrecipes.html', tparams)


@login_required
@permission_required('app.change_food', raise_exception=True)
def food_edit(request, pk):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    role = get_user_role(request.user)
    food = get_object_or_404(Food, pk=pk, household=membership.household)

    if request.method == 'POST':
        form = FoodForm(request.POST, instance=food)
        if form.is_valid():
            updated_food = form.save(commit=False)
            updated_food.household = membership.household
            updated_food.save()
            return redirect('app:food_list')
    else:
        form = FoodForm(instance=food)

    return render(request, 'app/food/foodform.html', {
        'form': form,
        'role': role,
        'page_title': 'Edit food',
        'submit_label': 'Update',
        'add_ingredient_url': reverse('app:ingredient_new'),
    })


@login_required
@permission_required('app.delete_food', raise_exception=True)
def food_delete(request, pk):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    food = get_object_or_404(Food, pk=pk, household=membership.household)

    if request.method == 'POST':
        food.delete()
        return redirect('app:food_list')

    return render(request, 'app/food/food_confirm_delete.html', {
        'food': food,
    })


@login_required
@permission_required('app.mark_food_consumed', raise_exception=True)
def food_consume(request, pk):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    food = get_object_or_404(Food, pk=pk, household=membership.household)

    if request.method == 'POST':
        form = FoodQuantityForm(request.POST, food=food)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']

            if quantity == food.quantity:
                food.delete()
            else:
                food.quantity -= quantity
                food.save()

            return redirect('app:food_list')
    else:
        form = FoodQuantityForm(food=food)

    return render(request, 'app/food/food_action.html', {
        'form': form,
        'food': food,
        'page_title': 'Mark food as consumed',
        'submit_label': 'Confirm consumption',
    })


@login_required
@permission_required('app.mark_food_wasted', raise_exception=True)
def food_waste(request, pk):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    food = get_object_or_404(Food, pk=pk, household=membership.household)

    if request.method == 'POST':
        form = WasteForm(request.POST, food=food)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            WasteLog.objects.create(
                household=food.household,
                food=food,
                ingredient=food.ingredient,
                quantity=quantity,
                reason=reason,
                user=request.user,
            )

            if quantity == food.quantity:
                food.delete()
            else:
                food.quantity -= quantity
                food.save()

            return redirect('app:food_list')
    else:
        form = WasteForm(food=food)

    return render(request, 'app/food/food_action.html', {
        'form': form,
        'food': food,
        'page_title': 'Mark food as wasted',
        'submit_label': 'Confirm waste',
    })


@login_required
@permission_required('app.manage_household_members', raise_exception=True)
def household_members(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    members = (
        HouseholdMember.objects
        .select_related('user', 'household')
        .filter(household=membership.household)
        .order_by('user__username')
    )

    tparams = {
        'membership': membership,
        'members': members,
        'available_roles': ['HouseholdAdmin', 'InventoryManager', 'Member', 'Viewer'],
        'role': get_user_role(request.user),
    }

    return render(request, 'app/members/member_list.html', tparams)

@login_required
@permission_required('app.change_member_role', raise_exception=True)
def household_member_change_role(request, member_id):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    target_membership = get_object_or_404(
        HouseholdMember.objects.select_related('user', 'household'),
        pk=member_id,
        household=membership.household,
    )

    if request.method != 'POST':
        return redirect('app:household_members')

    form = MemberRoleForm(request.POST)
    if form.is_valid():
        new_role = form.cleaned_data['role']
        assign_user_role(target_membership.user, new_role)
        messages.success(
            request,
            f'Role for {target_membership.user.username} updated to {new_role}.'
        )
    else:
        messages.error(request, 'Invalid role selected.')

    return redirect('app:household_members')


@login_required
@permission_required('app.manage_household_members', raise_exception=True)
def household_member_add(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    if request.method == 'POST':
        form = HouseholdMemberCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data.get('email', '')
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.save()

            HouseholdMember.objects.create(
                user=user,
                household=membership.household,
            )

            assign_user_role(user, form.cleaned_data['role'])

            messages.success(
                request,
                f'User {user.username} was added to the household.'
            )
            return redirect('app:household_members')
    else:
        form = HouseholdMemberCreateForm()

    return render(request, 'app/members/member_add.html', {
        'form': form,
        'membership': membership,
        'role': get_user_role(request.user),
    })