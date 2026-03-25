# To access JSON data (views.py)
```python

def home(request):
    json_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'eurocv.json')

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cv = data['eurocv']
    personal = cv['personalInfo']
    work = cv['workexperience']['position']

    emails = contact.get('email', [])
    email_list = [f"{e['type']}: {e['value']}" for e in emails]

    activities = work['activities']['activity']

    context = {
        'foto': cv.get('foto', ''),
        'desired_employ': cv.get('desiredEmploy', ''),
        'name': f"{personal['name']['lastname']} {personal['name']['firstname']}",
        'wexp_dates': f"{work['dates']['start']['month']} {work['dates']['start']['year']} - {work['dates']['end']['month']} {work['dates']['end']['year']}",
    }

    return render(request, 'eurocv.html', context)
```

# Models.py (for DB)

```python
class Book(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    authors = models.ManyToManyField(Author)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.title
```
## admin.py
admin.site.register(Book)

## create superuser
python manage.py createsuperuser

## access Django Admin Site
http://localhost:{port}/admin

