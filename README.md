# Pantry Helper

Pantry Helper is a Django web application for managing household pantry items, tracking expiry dates and food waste, and suggesting recipes based on the ingredients currently available.

## Features

- User authentication with login/logout
- Household-based pantry management
- Different user roles with different permissions:
  - Viewer
  - Member
  - InventoryManager
  - HouseholdAdmin
- Add, edit, consume, waste, and delete pantry items
- Track expiry dates and reduce food waste
- Recipe management
- Suggested recipes based on ingredients available in the pantry
- Demo data support for presentation/testing

## Tech Stack

- Python
- Django
- SQLite
- HTML templates + CSS
- Django ORM
- Django Forms


## Setup

### 1. Clone the repository

```bash
git clone https://github.com/AnaSL-WRK/Pantry_Helper.git
cd Pantry_Helper/pantry_helper
```

### 2. Create and activate a virtual environment

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install django
```

### 4. Apply migrations

```bash
python manage.py migrate
```


### 5. Load recipe data and their ingredients

```bash
python manage.py load_recipes_from_json --create-missing
```

### 7. Run the development server

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Demo Data

This project also creates a demo user, demo household, and sample pantry items for demonstration purposes with the following command

```bash
python manage.py load_demo_data
```

### Demo account

```text
Username: demo_client
Password: demo1234
```
