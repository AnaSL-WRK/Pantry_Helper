from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


from .models import Food, Ingredient, Category, WasteLog, Household, HouseholdMember
from .utils import get_user_role, ROLE_GROUPS

# forms

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'category']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()

        if not name:
            raise ValidationError('Ingredient name is required.')

        normalized_name = ' '.join(name.split())

        if Ingredient.objects.filter(name__iexact=normalized_name).exists():
            raise ValidationError('This ingredient already exists.')

        return normalized_name


class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['ingredient', 'quantity', 'unit', 'location', 'expiry_date', 'notes']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ingredient'].queryset = Ingredient.objects.select_related('category').order_by('name')
        self.fields['ingredient'].empty_label = 'Select an ingredient'

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if quantity is None or quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')

        return quantity
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')

        if expiry_date and expiry_date < timezone.localdate():
            if not self.instance.pk:
                raise ValidationError('Expiry date cannot be in the past.')

        return expiry_date


class FoodQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        self.food = kwargs.pop('food', None)
        super().__init__(*args, **kwargs)

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if self.food and quantity and quantity > self.food.quantity:
            raise ValidationError('Quantity cannot be greater than the current quantity.')

        return quantity


class WasteForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
    reason = forms.ChoiceField(choices=WasteLog.WasteReason.choices)

    def __init__(self, *args, **kwargs):
        self.food = kwargs.pop('food', None)
        super().__init__(*args, **kwargs)

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if self.food and quantity and quantity > self.food.quantity:
            raise ValidationError('Quantity cannot be greater than the current quantity.')

        return quantity
    


class MemberRoleForm(forms.Form):
    role = forms.ChoiceField(
        choices=[(role, role) for role in ROLE_GROUPS],
        label='Role'
    )


class HouseholdMemberCreateForm(UserCreationForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(
        choices=[(role, role) for role in ROLE_GROUPS],
        label='Role'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('A user with this username already exists.')

        return username
    

class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ['name', 'description']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        normalized_name = ' '.join(name.split())

        if not normalized_name:
            raise ValidationError('Household name is required.')

        return normalized_name