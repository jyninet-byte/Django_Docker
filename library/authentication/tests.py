"""Tests for views and templates of the library app."""
import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from author.models import Author
from book.models import Book
from order.models import Order

from .models import CustomUser


class LibraryViewsTest(TestCase):
    def setUp(self):
        self.librarian = CustomUser.objects.create_user(
            email='lib@test.com', password='secret123', first_name='Olena', middle_name='',
            last_name='Koval', role=1, is_active=True)
        self.reader = CustomUser.objects.create_user(
            email='reader@test.com', password='secret123', first_name='Andrii', middle_name='',
            last_name='Melnyk', role=0, is_active=True)
        self.orwell = Author.objects.create(name='George', surname='Orwell', patronymic='')
        self.free_author = Author.objects.create(name='Free', surname='Author', patronymic='')
        self.book = Book.objects.create(name='1984', description='Dystopia', count=1)
        self.book.authors.add(self.orwell)
        self.other = Book.objects.create(name='Kobzar', description='Poetry', count=3)

    def login(self, user):
        self.client.force_login(user)

    # ---------- auth
    def test_register_reader_and_librarian(self):
        for role, email in (('0', 'new@test.com'), ('1', 'newlib@test.com')):
            self.client.logout()
            response = self.client.post(reverse('register'), {
                'first_name': 'Ivan', 'middle_name': '', 'last_name': 'Petrenko',
                'email': email, 'password1': 'secret123', 'password2': 'secret123', 'role': role})
            self.assertRedirects(response, reverse('book_list'))
            user = CustomUser.objects.get(email=email)
            self.assertEqual(user.role, int(role))
            self.assertTrue(user.check_password('secret123'))
            self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_register_errors(self):
        response = self.client.post(reverse('register'), {
            'first_name': '', 'last_name': 'X', 'email': 'reader@test.com',
            'password1': '1', 'password2': '2', 'role': '0'})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('already exists', form.errors['email'][0])
        self.assertIn('first_name', form.errors)
        self.assertIn('password1', form.errors)

    def test_login_logout(self):
        response = self.client.post(reverse('login'), {'email': 'reader@test.com', 'password': 'secret123'})
        self.assertRedirects(response, reverse('book_list'))
        response = self.client.post(reverse('login'), {'email': 'reader@test.com', 'password': 'bad'})
        self.client.logout()
        response = self.client.post(reverse('login'), {'email': 'reader@test.com', 'password': 'bad'})
        self.assertContains(response, 'Wrong email or password')
        self.login(self.reader)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('book_list'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('book_list'))

    # ---------- books
    def test_book_list_and_filters(self):
        self.login(self.reader)
        response = self.client.get(reverse('book_list'))
        self.assertContains(response, '1984')
        self.assertContains(response, 'Kobzar')
        response = self.client.get(reverse('book_list'), {'q': 'kob'})
        self.assertNotContains(response, '>1984<')
        self.assertContains(response, 'Kobzar')
        response = self.client.get(reverse('book_list'), {'author': self.orwell.id})
        self.assertEqual(list(response.context['books']), [self.book])
        response = self.client.get(reverse('book_list'), {'description': 'poet'})
        self.assertEqual(list(response.context['books']), [self.other])

    def test_book_detail(self):
        self.login(self.reader)
        response = self.client.get(reverse('book_detail', args=[self.book.id]))
        self.assertContains(response, 'Order the book')
        self.assertEqual(self.client.get(reverse('book_detail', args=[999])).status_code, 404)

    def test_user_books_only_for_librarian(self):
        Order.objects.create(user=self.reader, book=self.book, plated_end_at=timezone.now())
        self.login(self.reader)
        self.assertEqual(self.client.get(reverse('user_books', args=[self.reader.id])).status_code, 403)
        self.login(self.librarian)
        response = self.client.get(reverse('user_books', args=[self.reader.id]))
        self.assertContains(response, '1984')

    def test_book_create(self):
        self.login(self.librarian)
        response = self.client.post(reverse('book_create'), {
            'name': 'Animal Farm', 'description': 'Satire', 'count': '2', 'authors': [self.orwell.id]})
        book = Book.objects.get(name='Animal Farm')
        self.assertRedirects(response, reverse('book_detail', args=[book.id]))
        self.assertEqual(list(book.authors.all()), [self.orwell])

    # ---------- users
    def test_users_only_for_librarian(self):
        self.login(self.reader)
        self.assertEqual(self.client.get(reverse('user_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('user_detail', args=[self.reader.id])).status_code, 403)
        self.login(self.librarian)
        self.assertContains(self.client.get(reverse('user_list')), 'reader@test.com')
        self.assertContains(self.client.get(reverse('user_detail', args=[self.reader.id])), 'Melnyk')

    # ---------- orders
    def test_create_and_close_order(self):
        self.login(self.reader)
        date = (timezone.localdate() + datetime.timedelta(days=14)).isoformat()
        response = self.client.post(reverse('order_create'), {'book_id': self.book.id, 'plated_end_at': date})
        self.assertRedirects(response, reverse('my_orders'))
        order = Order.objects.get(user=self.reader, book=self.book)
        self.assertContains(self.client.get(reverse('my_orders')), '1984')

        # the only copy is taken now
        other_reader = CustomUser.objects.create_user(
            email='r2@test.com', password='secret123', first_name='A', middle_name='', last_name='B',
            is_active=True)
        self.login(other_reader)
        self.client.post(reverse('order_create'), {'book_id': self.book.id, 'plated_end_at': date})
        self.assertEqual(Order.objects.filter(book=self.book).count(), 1)

        # reader cannot close an order, librarian can
        self.assertEqual(self.client.post(reverse('order_close', args=[order.id])).status_code, 403)
        self.login(self.librarian)
        self.assertContains(self.client.get(reverse('order_list')), '1984')
        self.client.post(reverse('order_close', args=[order.id]))
        order.refresh_from_db()
        self.assertIsNotNone(order.end_at)

    def test_order_wrong_date(self):
        self.login(self.reader)
        self.client.post(reverse('order_create'), {'book_id': self.book.id, 'plated_end_at': '2000-01-01'})
        self.assertFalse(Order.objects.exists())

    def test_librarian_cannot_create_order_and_reader_cannot_see_all(self):
        self.login(self.librarian)
        response = self.client.post(reverse('order_create'), {'book_id': self.book.id, 'plated_end_at': '2099-01-01'})
        self.assertEqual(response.status_code, 403)
        self.login(self.reader)
        self.assertEqual(self.client.get(reverse('order_list')).status_code, 403)

    # ---------- authors
    def test_authors(self):
        self.login(self.reader)
        self.assertEqual(self.client.get(reverse('author_list')).status_code, 403)
        self.login(self.librarian)
        self.assertContains(self.client.get(reverse('author_list')), 'Orwell')

        self.client.post(reverse('author_create'), {'name': 'Ray', 'surname': 'Bradbury', 'patronymic': ''})
        self.assertTrue(Author.objects.filter(surname='Bradbury').exists())
        response = self.client.post(reverse('author_create'), {'name': '', 'surname': 'X' * 30})
        self.assertEqual(response.status_code, 400)

        self.client.post(reverse('author_delete', args=[self.orwell.id]))
        self.assertTrue(Author.objects.filter(pk=self.orwell.id).exists())
        self.client.post(reverse('author_delete', args=[self.free_author.id]))
        self.assertFalse(Author.objects.filter(pk=self.free_author.id).exists())

    def test_home_page(self):
        self.assertContains(self.client.get(reverse('home')), 'Every book in one place')


class FormsEditTest(TestCase):
    """Adding and editing with Django forms."""

    def setUp(self):
        self.librarian = CustomUser.objects.create_user(
            email='lib@test.com', password='secret123', first_name='Olena', middle_name='',
            last_name='Koval', role=1, is_active=True)
        self.reader = CustomUser.objects.create_user(
            email='reader@test.com', password='secret123', first_name='Andrii', middle_name='',
            last_name='Melnyk', role=0, is_active=True)
        self.author = Author.objects.create(name='George', surname='Orwell', patronymic='')
        self.other = Author.objects.create(name='Ray', surname='Bradbury', patronymic='')
        self.book = Book.objects.create(name='1984', description='Dystopia', count=2, year=1949)
        self.author.books.add(self.book)

    def test_forms_on_get(self):
        self.client.force_login(self.librarian)
        for url, form_class in ((reverse('book_create'), 'BookForm'),
                                (reverse('book_edit', args=[self.book.id]), 'BookForm'),
                                (reverse('author_edit', args=[self.author.id]), 'AuthorForm'),
                                (reverse('user_edit', args=[self.reader.id]), 'UserEditForm'),
                                (reverse('profile_edit'), 'ProfileForm')):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(type(response.context['form']).__name__, form_class)
        response = self.client.get(reverse('book_edit', args=[self.book.id]))
        self.assertEqual(response.context['form'].initial['name'], '1984')

    def test_book_edit(self):
        self.client.force_login(self.librarian)
        response = self.client.post(reverse('book_edit', args=[self.book.id]), {
            'name': 'Nineteen Eighty-Four', 'description': 'Classic', 'year': '1949', 'count': '5',
            'authors': [self.author.id, self.other.id]})
        self.assertRedirects(response, reverse('book_detail', args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, 'Nineteen Eighty-Four')
        self.assertEqual(self.book.count, 5)
        self.assertEqual(set(self.book.authors.all()), {self.author, self.other})

    def test_book_edit_errors(self):
        Order.objects.create(user=self.reader, book=self.book, plated_end_at=timezone.now())
        self.client.force_login(self.librarian)
        response = self.client.post(reverse('book_edit', args=[self.book.id]), {
            'name': '', 'description': '', 'year': '3000', 'count': '0'})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertIn('name', errors)
        self.assertIn('year', errors)
        self.assertIn('count', errors)

    def test_author_edit_and_duplicate(self):
        self.client.force_login(self.librarian)
        response = self.client.post(reverse('author_edit', args=[self.author.id]),
                                    {'surname': 'Orwell', 'name': 'Eric', 'patronymic': 'Arthur'})
        self.assertRedirects(response, reverse('author_list'))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, 'Eric')
        response = self.client.post(reverse('author_create'),
                                    {'surname': 'Bradbury', 'name': 'Ray', 'patronymic': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', str(response.context['form'].non_field_errors()))

    def test_profile_and_user_edit(self):
        self.client.force_login(self.reader)
        self.client.post(reverse('profile_edit'), {'first_name': 'Andriy', 'last_name': 'Melnyk', 'middle_name': 'I.'})
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.first_name, 'Andriy')
        self.assertEqual(self.client.get(reverse('user_edit', args=[self.reader.id])).status_code, 403)

        self.client.force_login(self.librarian)
        response = self.client.post(reverse('user_edit', args=[self.reader.id]), {
            'first_name': 'Andriy', 'last_name': 'Melnyk', 'middle_name': '', 'role': '1', 'is_active': 'on'})
        self.assertRedirects(response, reverse('user_detail', args=[self.reader.id]))
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.role, 1)

    def test_order_create_errors_and_extend(self):
        self.client.force_login(self.reader)
        response = self.client.post(reverse('order_create'), {'book_id': self.book.id, 'plated_end_at': '2000-01-01'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('plated_end_at', response.context['order_form'].errors)

        date = (timezone.localdate() + datetime.timedelta(days=7)).isoformat()
        self.client.post(reverse('order_create'), {'book_id': self.book.id, 'plated_end_at': date})
        order = Order.objects.get(user=self.reader, book=self.book)

        new_date = timezone.localdate() + datetime.timedelta(days=20)
        response = self.client.post(reverse('order_extend', args=[order.id]), {'plated_end_at': new_date.isoformat()})
        self.assertRedirects(response, reverse('my_orders'))
        order.refresh_from_db()
        self.assertEqual(timezone.localtime(order.plated_end_at).date(), new_date)

        too_late = timezone.localdate() + datetime.timedelta(days=90)
        response = self.client.post(reverse('order_extend', args=[order.id]), {'plated_end_at': too_late.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertIn('plated_end_at', response.context['form'].errors)

    def test_order_edit_by_librarian(self):
        order = Order.objects.create(user=self.reader, book=self.book,
                                     plated_end_at=timezone.now() + datetime.timedelta(days=5))
        self.client.force_login(self.librarian)
        returned = timezone.localtime(timezone.now()).strftime('%Y-%m-%dT%H:%M')
        planned = timezone.localtime(order.plated_end_at).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('order_edit', args=[order.id]),
                                    {'plated_end_at': planned, 'end_at': returned})
        self.assertRedirects(response, reverse('order_list'))
        order.refresh_from_db()
        self.assertIsNotNone(order.end_at)

        response = self.client.post(reverse('order_edit', args=[order.id]),
                                    {'plated_end_at': '2000-01-01T10:00', 'end_at': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('plated_end_at', response.context['form'].errors)


class AdminPanelTest(TestCase):
    """The admin panel opens for a superuser and shows all models."""

    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(email='admin@test.com', password='admin12345')
        self.author = Author.objects.create(name='George', surname='Orwell', patronymic='')
        self.book = Book.objects.create(name='1984', description='Dystopia', count=2, year=1949)
        self.author.books.add(self.book)
        self.order = Order.objects.create(user=self.admin, book=self.book,
                                          plated_end_at=timezone.now() + datetime.timedelta(days=7))
        self.client.force_login(self.admin)

    def test_superuser_flags(self):
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.is_active)

    def test_all_models_registered(self):
        response = self.client.get('/admin/')
        for name in ('Users', 'Authors', 'Books', 'Orders'):
            self.assertContains(response, name)

    def test_changelists_and_filters(self):
        urls = [
            '/admin/authentication/customuser/', '/admin/author/author/', '/admin/book/book/',
            '/admin/order/order/',
            f'/admin/order/order/?book_id={self.book.id}',
            f'/admin/order/order/?book__id__exact={self.book.id}',
            f'/admin/order/order/?book__authors__id__exact={self.author.id}',
            f'/admin/book/book/?authors__id__exact={self.author.id}',
            '/admin/book/book/?letter=1', '/admin/book/book/?q=1984', '/admin/author/author/?has_books=no',
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_detail_pages(self):
        response = self.client.get(f'/admin/book/book/{self.book.id}/change/')
        self.assertContains(response, 'Permanent information')
        self.assertContains(response, 'Changing information')
        self.assertContains(response, 'Issues of this book')
        response = self.client.get(f'/admin/author/author/{self.author.id}/change/')
        self.assertContains(response, 'Books in detail')
        self.assertEqual(self.client.get(f'/admin/order/order/{self.order.id}/change/').status_code, 200)
        self.assertEqual(self.client.get(f'/admin/authentication/customuser/{self.admin.id}/change/').status_code, 200)

    def test_add_user_in_admin_hashes_password(self):
        response = self.client.post('/admin/authentication/customuser/add/', {
            'email': 'staff@test.com', 'first_name': 'Ira', 'middle_name': '', 'last_name': 'Shevchuk',
            'role': '1', 'password1': 'Strong-pass-123', 'password2': 'Strong-pass-123',
            'orders-TOTAL_FORMS': '0', 'orders-INITIAL_FORMS': '0',
            'order_set-TOTAL_FORMS': '0', 'order_set-INITIAL_FORMS': '0'})
        errors = response.context['adminform'].form.errors if response.status_code == 200 else None
        self.assertEqual(response.status_code, 302, errors)
        user = CustomUser.objects.get(email='staff@test.com')
        self.assertTrue(user.check_password('Strong-pass-123'))
        self.assertTrue(user.is_active)

    def test_change_book_authors(self):
        other = Author.objects.create(name='Ray', surname='Bradbury', patronymic='')
        data = {
            'name': '1984', 'description': 'Dystopia', 'year': '1949', 'count': '3',
            'authors': [self.author.id, other.id],
            'order_set-TOTAL_FORMS': '1', 'order_set-INITIAL_FORMS': '1',
            'order_set-MIN_NUM_FORMS': '0', 'order_set-MAX_NUM_FORMS': '1000',
            'order_set-0-id': self.order.id, 'order_set-0-book': self.book.id,
            'order_set-0-user': self.admin.id,
            'order_set-0-plated_end_at_0': '2030-01-01', 'order_set-0-plated_end_at_1': '12:00:00',
            'order_set-0-end_at_0': '', 'order_set-0-end_at_1': '',
        }
        response = self.client.post(f'/admin/book/book/{self.book.id}/change/', data)
        self.assertEqual(response.status_code, 302, response.content[:3000])
        self.book.refresh_from_db()
        self.assertEqual(self.book.count, 3)
        self.assertEqual(set(self.book.authors.all()), {self.author, other})

    def test_close_orders_action(self):
        self.client.post('/admin/order/order/', {'action': 'close_orders', '_selected_action': [self.order.id]})
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.end_at)
