# Create venv and install Django
python3 -m venv venv
source venv/bin/activate
or 
venv\Scripts\activate
pip install django

# Start django proj in venv
>create project folder first
python -m django startproject pantry_helper .

# See server 
python manage.py runserver

# Create app folder with default files 
>go to django proj folder first
python manage.py startapp app


# Django project structure 
```
webproj/ ------ Pasta para o projeto. Pode ter qualquer nome.
    manage.py -- Utilitário em commando de linha para interagir com o projeto.

webproj/ --- Pacote do projeto. Nome usado para imports.
    __init__.py --- Ficheiro que define esta pasta como um pacote, em Python.
    settings.py --- Configurações do projeto Django.    
    urls.py ------- Mapping/routing das URLs para este projeto.
    wsgi.py ------- Um ponto de entrada para webservers compatíveis com WSGI.
    
app/ ------- Aplicação web individual, podendo coexistir várias.
    templates/ ---- Ficheiros HTML, invocados pelas views.
    static/ ------- CSS, JS, imagens, etc. – configurável em “settings.py”
    __init__.py -- Ficheiro que define esta pasta como um pacote, em Python.
    views.py ------ Recebe os pedidos dos clientes e devolve as respostas.
    models.py ----- Modelos dos dados.
    admin.py ------ Criação automática de interface para o modelo de dados.
    forms.py ------ Permite a receção de dados enviados pelos clients.
```

# Templates (if not found)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',   
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ os.path.join(BASE_DIR, 'app/templates') ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# For Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
## After defining models
python manage.py check
python manage.py makemigrations app
python manage.py migrate


# Vscode documentation on Django 
https://code.visualstudio.com/docs/python/tutorial-django