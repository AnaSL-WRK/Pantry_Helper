from django.shortcuts import redirect, render
from .utils import user_has_role, get_user_role
from .forms import CategoryForm, ItemForm
from .models import Item, Category

# Create your views here.

def home(request):
    return render(request, 'app/home.html')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    membership = None
    role = get_user_role(request.user)
    items = []

    if hasattr(request.user, 'household_member'):
        membership = request.user.household_member
        items = Item.objects.filter(
            household=membership.household
        ).order_by('expiry_date', 'name')[:5]

    tparams = {
        'membership': membership,
        'role': role,
        'items': items,
    }

    return render(request, 'app/dashboard.html', tparams)


def category_new(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not (user_has_role(request.user, 'HouseholdAdmin') or user_has_role(request.user, 'InventoryManager')):
        return redirect('/dashboard/')

    if not hasattr(request.user, 'household_member'):
        return redirect('/dashboard/')

    membership = request.user.household_member
    role = get_user_role(request.user)

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.household = membership.household
            category.save()
            return redirect('app:item_list')
    else:
        form = CategoryForm()

    tparams = {
        'form': form,
        'role': role,
    }

    return render(request, 'app/categoryform.html', tparams)


def item_list(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not hasattr(request.user, 'household_member'):
        return redirect('/dashboard/')

    membership = request.user.household_member
    role = get_user_role(request.user)

    items = Item.objects.filter(
        household=membership.household
    ).order_by('expiry_date', 'name')

    tparams = {
        'items': items,
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/itemlist.html', tparams)


def item_new(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not (user_has_role(request.user, 'HouseholdAdmin') or user_has_role(request.user, 'InventoryManager')):
        return redirect('/dashboard/')

    if not hasattr(request.user, 'household_member'):
        return redirect('/dashboard/')

    membership = request.user.household_member
    role = get_user_role(request.user)

    if request.method == 'POST':
        form = ItemForm(request.POST)
        form.fields['category'].queryset = Category.objects.filter(household=membership.household)

        if form.is_valid():
            item = form.save(commit=False)
            item.household = membership.household
            item.added_by = request.user
            item.save()
            return redirect('app:item_list')
    else:
        form = ItemForm()
        form.fields['category'].queryset = Category.objects.filter(household=membership.household)

    tparams = {
        'form': form,
        'role': role,
    }

    return render(request, 'app/itemform.html', tparams)