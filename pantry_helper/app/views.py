from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Q, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import FoodForm, FoodQuantityForm, HouseholdForm, HouseholdMemberCreateForm, IngredientForm, MemberRoleForm, WasteForm, RecipeForm, RecipeIngredientFormSet, RecipeStepFormSet
from .models import Food, Household, HouseholdMember, Ingredient, Recipe, WasteLog, RecipeIngredient, RecipeStep
from .utils import assign_user_role, get_membership, get_user_role


AVAILABLE_ROLES = ['HouseholdAdmin', 'InventoryManager', 'Member', 'Viewer']


def _get_available_foods_for_household(household):
    return Food.objects.select_related('ingredient').filter(
        household=household,
        quantity__gte=1,
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

    recipes = (
        Recipe.objects.filter(
            is_preloaded=True,
            household__isnull=True,
        )
        .prefetch_related('recipe_ingredients__ingredient')
        .order_by('name')
    )

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


def _get_household_admin_count(household):
    return (
        HouseholdMember.objects.filter(
            household=household,
            user__groups__name='HouseholdAdmin',
        )
        .distinct()
        .count()
    )


def _build_household_manage_context(request, membership, household_form=None, member_form=None):
    members = (
        HouseholdMember.objects.select_related('user', 'household')
        .filter(household=membership.household)
        .order_by('user__username')
    )

    members_with_roles = []
    for member in members:
        members_with_roles.append({
            'membership': member,
            'current_role': get_user_role(member.user),
        })

    return {
        'membership': membership,
        'role': get_user_role(request.user),
        'household_form': household_form or HouseholdForm(instance=membership.household),
        'member_form': member_form or HouseholdMemberCreateForm(),
        'members_with_roles': members_with_roles,
        'available_roles': AVAILABLE_ROLES,
        'can_edit_household': request.user.has_perm('app.change_household'),
        'can_manage_members': request.user.has_perm('app.manage_household_members'),
        'can_change_member_role': request.user.has_perm('app.change_member_role'),
        'is_creating_household': False,
    }


def _ordered_foods_queryset(queryset):
    return queryset.annotate(
        expiry_sort_bucket=Case(
            When(expiry_date__isnull=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('expiry_sort_bucket', 'expiry_date', 'ingredient__name')

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
    top_wasted_ingredients = []

    if membership:
        today = timezone.localdate()
        expiring_limit = today + timedelta(days=7)

        foods = _ordered_foods_queryset(
            Food.objects.filter(
                household=membership.household,
                quantity__gte=1,
            ).select_related('ingredient')
        )[:5]

        expiring_foods = (
            Food.objects.filter(
                household=membership.household,
                quantity__gte=1,
                expiry_date__isnull=False,
                expiry_date__gte=today,
                expiry_date__lte=expiring_limit,
            )
            .select_related('ingredient')
            .order_by('expiry_date', 'ingredient__name')[:5]
        )

        expired_foods = (
            Food.objects.filter(
                household=membership.household,
                quantity__gte=1,
                expiry_date__isnull=False,
                expiry_date__lt=today,
            )
            .select_related('ingredient')
            .order_by('expiry_date', 'ingredient__name')[:5]
        )

        recipe_suggestions = _build_recipe_suggestions(
            membership.household,
            limit=5,
        )

        if request.user.has_perm('app.view_wastelog'):

            top_wasted_ingredients = (
                WasteLog.objects.filter(household=membership.household)
                .values('ingredient__name', 'unit')
                .annotate(total_wasted=Sum('quantity'))
                .order_by('-total_wasted', 'ingredient__name', 'unit')[:5]
            )

    tparams = {
        'membership': membership,
        'role': role,
        'foods': foods,
        'expiring_foods': expiring_foods,
        'expired_foods': expired_foods,
        'recipe_suggestions': recipe_suggestions,
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

    foods = _ordered_foods_queryset(
        Food.objects.filter(
            household=membership.household,
            quantity__gte=1,
        ).select_related('ingredient')
    )

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


def _get_visible_recipes_queryset(membership):
    base_queryset = Recipe.objects.select_related(
        'household',
        'created_by',
    ).prefetch_related(
        'recipe_ingredients__ingredient',
        'steps',
    )

    visible_filter = Q(is_preloaded=True, household__isnull=True)

    if membership is not None:
        visible_filter |= Q(household=membership.household)

    return base_queryset.filter(visible_filter).order_by('name')


def _save_recipe_children(recipe, ingredient_formset, step_formset):
    RecipeIngredient.objects.filter(recipe=recipe).delete()
    RecipeStep.objects.filter(recipe=recipe).delete()

    ingredient_position = 1
    for form in ingredient_formset.forms:
        if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
            continue

        if form.cleaned_data.get('DELETE'):
            continue

        ingredient = form.cleaned_data.get('ingredient')
        if ingredient is None:
            continue

        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            quantity=form.cleaned_data.get('quantity'),
            unit=(form.cleaned_data.get('unit') or '').strip(),
            line_text=(form.cleaned_data.get('line_text') or '').strip(),
            position=ingredient_position,
        )
        ingredient_position += 1

    step_position = 1
    for form in step_formset.forms:
        if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
            continue

        if form.cleaned_data.get('DELETE'):
            continue

        step_text = (form.cleaned_data.get('step_text') or '').strip()
        if not step_text:
            continue

        RecipeStep.objects.create(
            recipe=recipe,
            step_text=step_text,
            position=step_position,
        )
        step_position += 1


@login_required
@permission_required('app.view_recipe', raise_exception=True)
def recipe_list(request):
    membership = get_membership(request.user)
    role = get_user_role(request.user)

    recipe_filter = Q(is_preloaded=True, household__isnull=True)

    if membership is not None:
        recipe_filter |= Q(
            household=membership.household,
            is_preloaded=False,
        )

    recipes = Recipe.objects.filter(recipe_filter).order_by('name')

    tparams = {
        'recipes': recipes,
        'membership': membership,
        'role': role,
        'can_add_recipe': request.user.has_perm('app.add_recipe') and membership is not None,
    }

    return render(request, 'app/recipes/recipelist.html', tparams)

@login_required
@permission_required('app.view_recipe', raise_exception=True)
def recipe_detail(request, recipe_id):
    membership = get_membership(request.user)
    role = get_user_role(request.user)

    visible_filter = Q(is_preloaded=True, household__isnull=True)
    if membership is not None:
        visible_filter |= Q(household=membership.household)

    recipe = get_object_or_404(
        Recipe.objects.select_related(
            'household',
            'created_by',
        ).prefetch_related(
            'recipe_ingredients__ingredient',
            'steps',
        ),
        visible_filter,
        pk=recipe_id,
    )

    available_ingredient_ids = set()
    expiring_ingredient_ids = set()

    if membership:
        today = timezone.localdate()
        expiring_limit = today + timedelta(days=7)

        available_foods = Food.objects.filter(
            household=membership.household,
            quantity__gte=1,
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

    is_household_recipe = (
        membership is not None
        and recipe.household_id == membership.household_id
        and not recipe.is_preloaded
    )

    tparams = {
        'recipe': recipe,
        'recipe_ingredients': recipe_ingredients,
        'steps': recipe.steps.all(),
        'available_count': available_count,
        'missing_count': missing_count,
        'expiring_match_count': expiring_match_count,
        'membership': membership,
        'role': role,
        'is_household_recipe': is_household_recipe,
        'can_manage_recipe': is_household_recipe and request.user.has_perm('app.change_recipe'),
        'can_delete_recipe': is_household_recipe and request.user.has_perm('app.delete_recipe'),
    }

    return render(request, 'app/recipes/recipedetail.html', tparams)

@login_required
@permission_required('app.add_recipe', raise_exception=True)
def recipe_new(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    role = get_user_role(request.user)

    if request.method == 'POST':
        form = RecipeForm(request.POST)
        ingredient_formset = RecipeIngredientFormSet(request.POST, prefix='ingredients')
        step_formset = RecipeStepFormSet(request.POST, prefix='steps')

        if form.is_valid() and ingredient_formset.is_valid() and step_formset.is_valid():
            recipe = form.save(commit=False)
            recipe.household = membership.household
            recipe.created_by = request.user
            recipe.is_preloaded = False
            recipe.save()

            _save_recipe_children(recipe, ingredient_formset, step_formset)

            messages.success(request, 'Recipe created successfully.')
            return redirect('app:recipe_detail', recipe_id=recipe.pk)
    else:
        form = RecipeForm()
        ingredient_formset = RecipeIngredientFormSet(prefix='ingredients')
        step_formset = RecipeStepFormSet(prefix='steps')

    return render(request, 'app/recipes/recipeform.html', {
        'form': form,
        'ingredient_formset': ingredient_formset,
        'step_formset': step_formset,
        'membership': membership,
        'role': role,
        'page_title': 'Create recipe',
        'submit_label': 'Save recipe',
    })


@login_required
@permission_required('app.change_recipe', raise_exception=True)
def recipe_edit(request, recipe_id):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    role = get_user_role(request.user)

    recipe = get_object_or_404(
        Recipe,
        pk=recipe_id,
        household=membership.household,
        is_preloaded=False,
    )

    if request.method == 'POST':
        form = RecipeForm(request.POST, instance=recipe)
        ingredient_formset = RecipeIngredientFormSet(
            request.POST,
            instance=recipe,
            prefix='ingredients',
        )
        step_formset = RecipeStepFormSet(
            request.POST,
            instance=recipe,
            prefix='steps',
        )

        if form.is_valid() and ingredient_formset.is_valid() and step_formset.is_valid():
            form.save()
            _save_recipe_children(recipe, ingredient_formset, step_formset)

            messages.success(request, 'Recipe updated successfully.')
            return redirect('app:recipe_detail', recipe_id=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        ingredient_formset = RecipeIngredientFormSet(instance=recipe, prefix='ingredients')
        step_formset = RecipeStepFormSet(instance=recipe, prefix='steps')

    return render(request, 'app/recipes/recipeform.html', {
        'form': form,
        'ingredient_formset': ingredient_formset,
        'step_formset': step_formset,
        'membership': membership,
        'role': role,
        'page_title': 'Edit recipe',
        'submit_label': 'Update recipe',
        'recipe': recipe,
    })


@login_required
@permission_required('app.delete_recipe', raise_exception=True)
def recipe_delete(request, recipe_id):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    recipe = get_object_or_404(
        Recipe,
        pk=recipe_id,
        household=membership.household,
        is_preloaded=False,
    )

    if request.method == 'POST':
        recipe.delete()
        messages.success(request, 'Recipe deleted successfully.')
        return redirect('app:recipe_list')

    return render(request, 'app/recipes/recipe_confirm_delete.html', {
        'recipe': recipe,
        'membership': membership,
        'role': get_user_role(request.user),
    })


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
                unit=food.unit,
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
def household_manage(request):
    membership = get_membership(request.user)

    if membership is None:
        if request.method == 'POST':
            household_form = HouseholdForm(request.POST)
            if household_form.is_valid():
                household = household_form.save(commit=False)
                household.created_by = request.user
                household.save()

                HouseholdMember.objects.create(
                    user=request.user,
                    household=household,
                )

                assign_user_role(request.user, 'HouseholdAdmin')
                messages.success(request, 'Household created successfully.')
                return redirect('app:household_manage')
        else:
            household_form = HouseholdForm()

        return render(request, 'app/household/household_manage.html', {
            'membership': None,
            'role': get_user_role(request.user),
            'household_form': household_form,
            'member_form': None,
            'members_with_roles': [],
            'available_roles': AVAILABLE_ROLES,
            'can_edit_household': True,
            'can_manage_members': False,
            'can_change_member_role': False,
            'is_creating_household': True,
        })

    if not (
        request.user.has_perm('app.change_household')
        or request.user.has_perm('app.manage_household_members')
    ):
        return redirect('app:dashboard')

    if request.method == 'POST':
        if not request.user.has_perm('app.change_household'):
            messages.error(request, 'You do not have permission to edit this household.')
            return redirect('app:household_manage')

        household_form = HouseholdForm(request.POST, instance=membership.household)
        if household_form.is_valid():
            household_form.save()
            messages.success(request, 'Household updated successfully.')
            return redirect('app:household_manage')
    else:
        household_form = HouseholdForm(instance=membership.household)

    context = _build_household_manage_context(
        request,
        membership,
        household_form=household_form,
    )
    return render(request, 'app/household/household_manage.html', context)


@login_required
@permission_required('app.manage_household_members', raise_exception=True)
def household_members(request):
    return redirect('app:household_manage')


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
        return redirect('app:household_manage')

    form = MemberRoleForm(request.POST)
    if form.is_valid():
        new_role = form.cleaned_data['role']
        current_role = get_user_role(target_membership.user)

        if (
            current_role == 'HouseholdAdmin'
            and new_role != 'HouseholdAdmin'
            and _get_household_admin_count(membership.household) == 1
        ):
            messages.error(request, 'You cannot change the role of the last household admin.')
            return redirect('app:household_manage')

        assign_user_role(target_membership.user, new_role)
        messages.success(
            request,
            f'Role for {target_membership.user.username} updated to {new_role}.',
        )
    else:
        messages.error(request, 'Invalid role selected.')

    return redirect('app:household_manage')


@login_required
@permission_required('app.manage_household_members', raise_exception=True)
def household_member_add(request):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    if request.method != 'POST':
        return redirect('app:household_manage')

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
            f'User {user.username} was added to the household.',
        )
        return redirect('app:household_manage')

    context = _build_household_manage_context(
        request,
        membership,
        member_form=form,
    )
    return render(request, 'app/household/household_manage.html', context)


@login_required
def household_create(request):
    return household_manage(request)


@login_required
def household_edit(request):
    return household_manage(request)


@login_required
@permission_required('app.manage_household_members', raise_exception=True)
def household_member_remove(request, member_id):
    membership = get_membership(request.user)
    if membership is None:
        return redirect('app:dashboard')

    target_membership = get_object_or_404(
        HouseholdMember.objects.select_related('user', 'household'),
        pk=member_id,
        household=membership.household,
    )

    if request.method != 'POST':
        return redirect('app:household_manage')

    target_role = get_user_role(target_membership.user)

    if (
        target_role == 'HouseholdAdmin'
        and _get_household_admin_count(membership.household) == 1
    ):
        messages.error(request, 'You cannot remove the last household admin.')
        return redirect('app:household_manage')

    removed_username = target_membership.user.username
    target_user = target_membership.user

    target_membership.delete()
    target_user.groups.clear()

    messages.success(request, f'{removed_username} was removed from the household.')
    return redirect('app:household_manage')