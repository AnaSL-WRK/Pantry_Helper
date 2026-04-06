source venv/bin/activate


python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py load_recipes_from_json 
python manage.py load_recipes_from_json --create-missing

demo_client
demo1234

python manage.py migrate
python manage.py load_recipes_from_json --create-missing
python manage.py runserver


