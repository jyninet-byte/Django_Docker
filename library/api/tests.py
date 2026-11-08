"""Tests for the REST API (CRUD for user, user/{id}/order, order, book, author)."""
import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import CustomUser
from author.models import Author
from book.models import Book
from order.models import Order

API = '/api/v1'


def future(days=14):
    return (timezone.now() + datetime.timedelta(days=days)).isoformat()


class ApiTestCase(APITestCase):
    def setUp(self):
        self.librarian = CustomUser.objects.create_user(
            email='lib@test.com', password='secret123', first_name='Olena', middle_name='',
            last_name='Koval', role=1, is_active=True)
        self.reader = CustomUser.objects.create_user(
            email='reader@test.com', password='secret123', first_name='Andrii', middle_name='',
            last_name='Melnyk', role=0, is_active=True)
        self.other_reader = CustomUser.objects.create_user(
            email='maria@test.com', password='secret123', first_name='Maria', middle_name='',
            last_name='Bondar', role=0, is_active=True)
        self.orwell = Author.objects.create(name='George', surname='Orwell', patronymic='')
        self.free_author = Author.objects.create(name='Lina', surname='Kostenko', patronymic='')
        self.book = Book.objects.create(name='1984', description='Dystopia', count=2, year=1949)
        self.orwell.books.add(self.book)
        self.single = Book.objects.create(name='Animal Farm', description='Satire', count=1, year=1945)
        self.order = Order.objects.create(user=self.reader, book=self.book, plated_end_at=future())

    def as_librarian(self):
        self.client.force_authenticate(self.librarian)

    def as_reader(self):
        self.client.force_authenticate(self.reader)


class AuthTest(ApiTestCase):
    def test_anonymous_gets_401_or_403(self):
        for url in ('user', 'order', 'book', 'author', f'user/{self.reader.id}/order'):
            response = self.client.get(f'{API}/{url}/')
            self.assertIn(response.status_code, (401, 403), url)

    def test_basic_auth_like_postman(self):
        self.client.credentials(HTTP_AUTHORIZATION='Basic bGliQHRlc3QuY29tOnNlY3JldDEyMw==')  # lib@test.com:secret123
        self.assertEqual(self.client.get(f'{API}/book/').status_code, 200)

    def test_url_without_trailing_slash(self):
        self.as_librarian()
        self.assertEqual(self.client.get(f'{API}/book').status_code, 200)
        self.assertEqual(self.client.get(f'{API}/book/{self.book.id}').status_code, 200)
        self.assertEqual(self.client.get(f'{API}/user/{self.reader.id}/order/{self.order.id}').status_code, 200)


class BookApiTest(ApiTestCase):
    def test_crud(self):
        self.as_librarian()
        # Create
        response = self.client.post(f'{API}/book/', {
            'name': 'Animal Farm 2', 'description': 'New', 'year': 2020, 'count': 3,
            'authors': [self.orwell.id]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        book_id = response.data['id']
        self.assertEqual(response.data['authors'], [self.orwell.id])
        # Read
        response = self.client.get(f'{API}/book/{book_id}/')
        self.assertEqual(response.data['name'], 'Animal Farm 2')
        self.assertEqual(response.data['available'], 3)
        # Update (PUT and PATCH)
        response = self.client.put(f'{API}/book/{book_id}/', {
            'name': 'Renamed', 'description': '', 'year': 2021, 'count': 4, 'authors': []}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['authors'], [])
        response = self.client.patch(f'{API}/book/{book_id}/', {'count': 7}, format='json')
        self.assertEqual(response.data['count'], 7)
        self.assertEqual(response.data['name'], 'Renamed')
        # Delete
        self.assertEqual(self.client.delete(f'{API}/book/{book_id}/').status_code, 204)
        self.assertEqual(self.client.get(f'{API}/book/{book_id}/').status_code, 404)

    def test_list_and_filters(self):
        self.as_reader()
        self.assertEqual(len(self.client.get(f'{API}/book/').data), 2)
        self.assertEqual(len(self.client.get(f'{API}/book/?name=farm').data), 1)
        self.assertEqual(len(self.client.get(f'{API}/book/?author={self.orwell.id}').data), 1)

    def test_validation(self):
        self.as_librarian()
        response = self.client.post(f'{API}/book/', {'name': '', 'count': 0, 'year': 3000}, format='json')
        self.assertEqual(response.status_code, 400)
        for field in ('name', 'count', 'year'):
            self.assertIn(field, response.data)

    def test_reader_cannot_change(self):
        self.as_reader()
        self.assertEqual(self.client.post(f'{API}/book/', {'name': 'X', 'count': 1}).status_code, 403)
        self.assertEqual(self.client.delete(f'{API}/book/{self.book.id}/').status_code, 403)


class AuthorApiTest(ApiTestCase):
    def test_crud(self):
        self.as_librarian()
        response = self.client.post(f'{API}/author/', {
            'name': 'Ray', 'surname': 'Bradbury', 'patronymic': '', 'books': [self.single.id]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        author_id = response.data['id']
        self.assertEqual(self.client.get(f'{API}/author/{author_id}/').data['books'], [self.single.id])
        response = self.client.patch(f'{API}/author/{author_id}/', {'books': []}, format='json')
        self.assertEqual(response.data['books'], [])
        response = self.client.put(f'{API}/author/{author_id}/', {
            'name': 'Raymond', 'surname': 'Bradbury', 'patronymic': 'Douglas'}, format='json')
        self.assertEqual(response.data['name'], 'Raymond')
        self.assertEqual(self.client.delete(f'{API}/author/{author_id}/').status_code, 204)

    def test_cannot_delete_author_with_books(self):
        self.as_librarian()
        self.assertEqual(self.client.delete(f'{API}/author/{self.orwell.id}/').status_code, 400)
        self.assertEqual(self.client.delete(f'{API}/author/{self.free_author.id}/').status_code, 204)

    def test_reader_read_only(self):
        self.as_reader()
        self.assertEqual(self.client.get(f'{API}/author/').status_code, 200)
        self.assertEqual(self.client.post(f'{API}/author/', {'name': 'A', 'surname': 'B'}).status_code, 403)


class UserApiTest(ApiTestCase):
    def test_crud_by_librarian(self):
        self.as_librarian()
        response = self.client.post(f'{API}/user/', {
            'email': 'new@test.com', 'password': 'secret123', 'first_name': 'Ivan',
            'middle_name': '', 'last_name': 'Petrenko', 'role': 0}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('password', response.data)
        user_id = response.data['id']
        self.assertTrue(CustomUser.objects.get(pk=user_id).check_password('secret123'))
        self.assertEqual(len(self.client.get(f'{API}/user/').data), 4)
        response = self.client.patch(f'{API}/user/{user_id}/', {'last_name': 'Shevchuk', 'password': 'newpass1'},
                                     format='json')
        self.assertEqual(response.data['last_name'], 'Shevchuk')
        self.assertTrue(CustomUser.objects.get(pk=user_id).check_password('newpass1'))
        self.assertEqual(self.client.delete(f'{API}/user/{user_id}/').status_code, 204)

    def test_duplicate_email_and_missing_password(self):
        self.as_librarian()
        response = self.client.post(f'{API}/user/', {'email': 'READER@test.com', 'first_name': 'A',
                                                     'last_name': 'B'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_reader_sees_only_himself(self):
        self.as_reader()
        response = self.client.get(f'{API}/user/')
        self.assertEqual([u['id'] for u in response.data], [self.reader.id])
        self.assertEqual(self.client.get(f'{API}/user/{self.other_reader.id}/').status_code, 404)
        response = self.client.patch(f'{API}/user/{self.reader.id}/', {'first_name': 'Andriy'}, format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(f'{API}/user/{self.reader.id}/', {'role': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(f'{API}/user/', {'email': 'x@x.com'}).status_code, 403)
        self.assertEqual(self.client.delete(f'{API}/user/{self.reader.id}/').status_code, 403)


class OrderApiTest(ApiTestCase):
    def test_crud_by_librarian(self):
        self.as_librarian()
        response = self.client.post(f'{API}/order/', {
            'user': self.other_reader.id, 'book': self.single.id, 'plated_end_at': future(7)}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        order_id = response.data['id']
        self.assertEqual(response.data['user'], self.other_reader.id)
        # the only copy is taken now
        response = self.client.post(f'{API}/order/', {
            'user': self.reader.id, 'book': self.single.id, 'plated_end_at': future(7)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('book', response.data)
        # close the order
        response = self.client.patch(f'{API}/order/{order_id}/', {'end_at': timezone.now().isoformat()}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(response.data['end_at'])
        self.assertEqual(len(self.client.get(f'{API}/order/').data), 2)
        self.assertEqual(self.client.delete(f'{API}/order/{order_id}/').status_code, 204)

    def test_wrong_dates(self):
        self.as_librarian()
        response = self.client.post(f'{API}/order/', {
            'user': self.reader.id, 'book': self.single.id, 'plated_end_at': '2000-01-01T10:00:00Z'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('plated_end_at', response.data)

    def test_reader_orders(self):
        self.as_reader()
        self.assertEqual([o['id'] for o in self.client.get(f'{API}/order/').data], [self.order.id])
        # reader creates an order for himself even if he sends another user
        response = self.client.post(f'{API}/order/', {
            'user': self.other_reader.id, 'book': self.single.id, 'plated_end_at': future(7)}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['user'], self.reader.id)
        self.assertEqual(self.client.patch(f'{API}/order/{self.order.id}/', {'end_at': None}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'{API}/order/{self.order.id}/').status_code, 403)


class UserOrderApiTest(ApiTestCase):
    def test_crud(self):
        self.as_librarian()
        url = f'{API}/user/{self.other_reader.id}/order/'
        self.assertEqual(self.client.get(url).data, [])
        response = self.client.post(url, {'book': self.book.id, 'plated_end_at': future(5)}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['user'], self.other_reader.id)
        order_id = response.data['id']
        self.assertEqual(len(self.client.get(url).data), 1)
        response = self.client.patch(f'{url}{order_id}/', {'plated_end_at': future(10)}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        # the order of another user is not found in this user's list
        self.assertEqual(self.client.get(f'{url}{self.order.id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'{url}{order_id}/').status_code, 204)
        self.assertEqual(self.client.get(f'{API}/user/999/order/').status_code, 404)

    def test_reader_only_own(self):
        self.as_reader()
        self.assertEqual(self.client.get(f'{API}/user/{self.reader.id}/order/').status_code, 200)
        self.assertEqual(self.client.get(f'{API}/user/{self.other_reader.id}/order/').status_code, 403)
