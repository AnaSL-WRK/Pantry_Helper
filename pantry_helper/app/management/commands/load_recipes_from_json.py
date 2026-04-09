import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from app.models import Category, Ingredient, Recipe, RecipeIngredient, RecipeStep


class Command(BaseCommand):
    help = "Load preloaded recipes from a JSON file into Recipe, RecipeIngredient, and RecipeStep."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            nargs="?",
            default="/static/wasteless_recipes_500.json",
            help="Path to the recipes JSON file.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing preloaded recipes before loading.",
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Create Ingredient rows if an ingredient name is missing.",
        )

    def handle(self, *args, **options):
        json_path = Path(options["json_path"])
        create_missing = options["create_missing"]

        if not json_path.exists():
            raise CommandError(f"File not found: {json_path}")

        with json_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)

        recipes_data = payload.get("recipes")
        if not isinstance(recipes_data, list):
            raise CommandError('JSON file must contain a top-level "recipes" list.')

        if options["clear"]:
            preloaded_recipes = Recipe.objects.filter(is_preloaded=True, household__isnull=True)
            RecipeIngredient.objects.filter(recipe__in=preloaded_recipes).delete()
            RecipeStep.objects.filter(recipe__in=preloaded_recipes).delete()
            deleted_count, _ = preloaded_recipes.delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} preloaded recipes."))

        category_cache = {c.name.casefold(): c for c in Category.objects.all()}

        created_recipes = 0
        updated_recipes = 0
        created_ingredients = 0
        updated_ingredients = 0
        missing_ingredients = 0

        for recipe_data in recipes_data:
            name = str(recipe_data.get("name", "")).strip()
            source_url = str(recipe_data.get("source_url", "")).strip()
            source_site = str(recipe_data.get("source_site", "")).strip()
            author = str(recipe_data.get("author", "")).strip()
            is_preloaded = bool(recipe_data.get("is_preloaded", True))

            if not name:
                continue

            recipe = None

            if source_url:
                recipe = Recipe.objects.filter(
                    source_url=source_url,
                    household__isnull=True
                ).first()

            if recipe is None:
                recipe = Recipe.objects.filter(
                    name=name,
                    household__isnull=True,
                    is_preloaded=True
                ).first()

            if recipe is None:
                recipe = Recipe.objects.create(
                    name=name,
                    author=author,
                    source_url=source_url,
                    source_site=source_site,
                    is_preloaded=is_preloaded,
                    household=None,
                    created_by=None,
                )
                created_recipes += 1
            else:
                recipe.name = name
                recipe.author = author
                recipe.source_url = source_url
                recipe.source_site = source_site
                recipe.is_preloaded = is_preloaded
                recipe.household = None
                recipe.created_by = None
                recipe.save()
                updated_recipes += 1

                recipe.recipe_ingredients.all().delete()
                recipe.steps.all().delete()

            ingredients_data = recipe_data.get("ingredients", [])
            for ingredient_data in sorted(ingredients_data, key=lambda x: x.get("position", 0)):
                ingredient_name = str(ingredient_data.get("item_name", "")).strip()
                category_name = str(ingredient_data.get("category", "")).strip()
                unit = str(ingredient_data.get("unit") or "").strip()
                line_text = str(ingredient_data.get("line_text") or "").strip()
                position = int(ingredient_data.get("position", 1) or 1)

                quantity_value = ingredient_data.get("quantity")
                quantity = None
                if quantity_value is not None:
                    try:
                        quantity = (int(quantity_value))
                    except (InvalidOperation, TypeError, ValueError):
                        quantity = None

                if not ingredient_name:
                    continue

                category = None
                if category_name:
                    category_key = category_name.casefold()
                    category = category_cache.get(category_key)
                    if category is None:
                        category, _ = Category.objects.get_or_create(name=category_name)
                        category_cache[category_key] = category

                ingredient = Ingredient.objects.filter(name__iexact=ingredient_name).first()

                if ingredient is None:
                    if create_missing:
                        ingredient = Ingredient.objects.create(
                            name=ingredient_name,
                            category=category
                        )
                        created_ingredients += 1
                    else:
                        missing_ingredients += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ingredient skipped: {ingredient_name}"
                                + (f" [{category_name}]" if category_name else "")
                            )
                        )
                        continue
                else:
                    if ingredient.category is None and category is not None:
                        ingredient.category = category
                        ingredient.save(update_fields=["category"])
                        updated_ingredients += 1

                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    quantity=quantity,
                    unit=unit,
                    line_text=line_text,
                    position=position,
                )

            steps_data = recipe_data.get("steps", [])
            for step_data in sorted(steps_data, key=lambda x: x.get("position", 0)):
                instruction = str(step_data.get("instruction", "")).strip()
                position = int(step_data.get("position", 1) or 1)

                if not instruction:
                    continue

                RecipeStep.objects.create(
                    recipe=recipe,
                    step_text=instruction,
                    position=position,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Recipes created={created_recipes}, "
                f"recipes updated={updated_recipes}, "
                f"ingredients created={created_ingredients}, "
                f"ingredients updated={updated_ingredients}, "
                f"missing ingredients skipped={missing_ingredients}"
            )
        )
