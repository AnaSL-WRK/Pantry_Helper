from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import BaseInlineFormSet, inlineformset_factory


from .models import Food, Ingredient, Category, WasteLog, Household, HouseholdMember, Recipe, RecipeIngredient, RecipeStep, Unit
from .utils import ROLE_GROUPS

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
            'unit': forms.Select(choices=Unit.choices),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ingredient'].queryset = Ingredient.objects.select_related('category').order_by('name')
        self.fields['ingredient'].empty_label = 'Select an ingredient'
        self.fields['unit'].choices = Unit.choices


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

        if self.food:
            self.fields['quantity'].label = f'Quantity ({self.food.unit})'
            self.fields['quantity'].help_text = f'Available: {self.food.quantity} {self.food.unit}'


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
    
class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'author', 'source_site', 'source_url']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        normalized_name = ' '.join(name.split())

        if not normalized_name:
            raise ValidationError('Recipe name is required.')

        return normalized_name

    def clean_author(self):
        return ' '.join(self.cleaned_data.get('author', '').split())

    def clean_source_site(self):
        return ' '.join(self.cleaned_data.get('source_site', '').split())


class BaseRecipeIngredientFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        has_ingredient = False
        seen_ingredients = set()

        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                continue

            if form.cleaned_data.get('DELETE'):
                continue

            ingredient = form.cleaned_data.get('ingredient')
            quantity = form.cleaned_data.get('quantity')
            unit = (form.cleaned_data.get('unit') or '').strip()
            line_text = (form.cleaned_data.get('line_text') or '').strip()

            if ingredient is None:
                if quantity or unit or line_text:
                    raise ValidationError('Select an ingredient for every filled ingredient row.')
                continue

            has_ingredient = True

            if ingredient.pk in seen_ingredients:
                raise ValidationError('Do not repeat the same ingredient in the recipe.')

            seen_ingredients.add(ingredient.pk)

            if quantity is not None and quantity <= 0:
                form.add_error('quantity', 'Quantity must be greater than 0.')

        if not has_ingredient:
            raise ValidationError('Add at least one ingredient.')


class BaseRecipeStepFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        has_step = False

        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                continue

            if form.cleaned_data.get('DELETE'):
                continue

            step_text = (form.cleaned_data.get('step_text') or '').strip()

            if step_text:
                has_step = True

        if not has_step:
            raise ValidationError('Add at least one step.')


RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    fields=['ingredient', 'quantity', 'unit', 'line_text'],
    formset=BaseRecipeIngredientFormSet,
    extra=1,
    can_delete=True,
    widgets={
        'unit': forms.Select(choices=[('', '---------')] + list(Unit.choices)),
        'line_text': forms.TextInput(attrs={'placeholder': 'Optional original ingredient line'}),
    },
)

RecipeStepFormSet = inlineformset_factory(
    Recipe,
    RecipeStep,
    fields=['step_text'],
    formset=BaseRecipeStepFormSet,
    extra=1,
    can_delete=True,
    widgets={
        'step_text': forms.Textarea(attrs={'rows': 2}),
    },
)