from django.shortcuts import redirect, render
from .utils import user_has_role, get_user_role
from .forms import FoodForm
from .models import Food


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

    if request.method == 'POST':
        form = FoodForm(request.POST)

        if form.is_valid():
            food = form.save(commit=False)
            food.household = membership.household
            food.added_by = request.user
            food.save()
            return redirect('app:food_list')
    else:
        form = FoodForm()

    tparams = {
        'form': form,
        'role': role,
    }

    return render(request, 'app/foodform.html', tparams)