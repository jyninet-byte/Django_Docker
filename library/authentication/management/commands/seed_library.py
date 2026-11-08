"""Fill the database with demo data: authors, books, two users and some orders.

Usage:  python manage.py seed_library
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from authentication.models import CustomUser
from author.models import Author
from book.models import Book
from order.models import Order

AUTHORS = [
    ('Taras', 'Shevchenko', 'Hryhorovych'),
    ('Lesya', 'Ukrainka', ''),
    ('Ivan', 'Franko', 'Yakovych'),
    ('Mykhailo', 'Kotsiubynsky', 'Mykhailovych'),
    ('George', 'Orwell', ''),
    ('Ray', 'Bradbury', ''),
    ('Robert', 'Martin', 'Cecil'),
    ('Mark', 'Lutz', ''),
    ('Lina', 'Kostenko', 'Vasylivna'),  # no books yet - can be removed
]

BOOKS = [
    ('Kobzar', 'A collection of poetry, the cornerstone of modern Ukrainian literature.', 5, ['Shevchenko']),
    ('The Forest Song', 'A drama-extravaganza about love, freedom and the spirit of the forest.', 3, ['Ukrainka']),
    ('Zakhar Berkut', 'A historical novel about a Carpathian community fighting the Mongol invasion.', 4, ['Franko']),
    ('Shadows of Forgotten Ancestors', 'A Hutsul love story full of folklore and mountain magic.', 2, ['Kotsiubynsky']),
    ('1984', 'A dystopian novel about total surveillance and the power of truth.', 6, ['Orwell']),
    ('Animal Farm', 'A satirical allegory about a revolution that went wrong.', 1, ['Orwell']),
    ('Fahrenheit 451', 'Firemen burn books in a society that has forgotten how to think.', 3, ['Bradbury']),
    ('Clean Code', 'A handbook of agile software craftsmanship.', 4, ['Martin']),
    ('Learning Python', 'A comprehensive introduction to the Python language.', 2, ['Lutz']),
    ('Ukrainian Classics Anthology', 'Selected works of the great Ukrainian writers.', 2, ['Shevchenko', 'Ukrainka', 'Franko']),
]

YEARS = {
    'Kobzar': 1840, 'The Forest Song': 1911, 'Zakhar Berkut': 1883,
    'Shadows of Forgotten Ancestors': 1911, '1984': 1949, 'Animal Farm': 1945,
    'Fahrenheit 451': 1953, 'Clean Code': 2008, 'Learning Python': 2013,
    'Ukrainian Classics Anthology': 2020,
}

USERS = [
    # email, password, first, middle, last, role
    ('librarian@library.com', 'librarian123', 'Olena', 'Petrivna', 'Koval', 1),
    ('reader@library.com', 'reader123', 'Andrii', 'Ivanovych', 'Melnyk', 0),
    ('maria@library.com', 'maria123', 'Maria', '', 'Bondar', 0),
]


class Command(BaseCommand):
    help = 'Fill the database with demo authors, books, users and orders.'

    def handle(self, *args, **options):
        authors = {}
        for name, surname, patronymic in AUTHORS:
            author, _ = Author.objects.get_or_create(name=name, surname=surname, patronymic=patronymic)
            authors[surname] = author

        books = {}
        for title, description, count, author_surnames in BOOKS:
            book, created = Book.objects.get_or_create(name=title, defaults={'description': description, 'count': count})
            if created:
                book.authors.add(*[authors[s] for s in author_surnames])
            if book.year is None and title in YEARS:
                book.year = YEARS[title]
                book.save()
            books[title] = book

        users = {}
        for email, password, first, middle, last, role in USERS:
            user = CustomUser.objects.filter(email=email).first()
            if user is None:
                user = CustomUser.objects.create_user(email=email, password=password, first_name=first,
                                                      middle_name=middle, last_name=last, role=role,
                                                      is_active=True)
            users[email] = user

        if not Order.objects.exists():
            now = timezone.now()
            reader, maria = users['reader@library.com'], users['maria@library.com']
            demo = [
                (reader, '1984', now + datetime.timedelta(days=10), None),
                (reader, 'Kobzar', now - datetime.timedelta(days=3), None),          # overdue
                (reader, 'Clean Code', now - datetime.timedelta(days=20), now - datetime.timedelta(days=22)),
                (maria, 'Animal Farm', now + datetime.timedelta(days=7), None),     # the only copy is taken
                (maria, 'The Forest Song', now + datetime.timedelta(days=14), None),
            ]
            for user, title, plated_end_at, end_at in demo:
                order = Order.objects.create(user=user, book=books[title], plated_end_at=plated_end_at)
                # created_at has auto_now_add, so set a realistic date with update()
                Order.objects.filter(pk=order.pk).update(
                    created_at=plated_end_at - datetime.timedelta(days=14), end_at=end_at)

        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
        self.stdout.write('Librarian: librarian@library.com / librarian123')
        self.stdout.write('Reader:    reader@library.com / reader123')
