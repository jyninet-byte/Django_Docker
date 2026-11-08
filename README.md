# Django_View-Templates

## install requirement project's packages

```commandline
pip install -r requirements.txt
```

## Run project

Go to the folder with manage.py file, run library
```commandline
python manage.py migrate 
```

```commandline
python manage.py runserver
```

## Run tests

There are no tests.

Everything is at your discretion and the feeling of beauty :)

**_As a result of this sprint ( except fot the code in  repository) you should have a short video (2-10min) that shows functionality of the app._**

## Tasks

Create the appropriate views and templates for:

**Do not use django forms, use only HTML forms!**

(if necessary, you can modify the models)

auth
* Provide the ability to register the user as a librarian or as an ordinary user (guest)
* Provide the ability to log in (guest)
* Provide the ability to Log out (authorized user)

books  (admin/user)

* show information about all books (admin/user)
* provide an opportunity to view a specific book (admin/user);
* provide the ability to filter books by various criteria (author, title, etc.) (admin/user);
* show all books provided to a specific user (by id) (admin);

users  (admin)

* show information about all users (admin/user)
* provide an opportunity to view a specific user (admin/user)

orders  (admin)

* show information about all orders (admin)
* show information about all my orders (user)
* provide an opportunity to create an order (user)
* provide an opportunity to close the order  (admin)

authors  (admin)

* show information about all authors (admin)
* provide an opportunity to create a new author  (admin)
* provide the ability to remove the author if he is not attached to any book (admin)

---

## Solution

### Setup
```commandline
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```
Create `library/library/local_settings.py` with your PostgreSQL connection data, then:
```commandline
cd library
python manage.py migrate
python manage.py seed_library    # demo authors, books, users and orders
python manage.py runserver
```

Demo accounts (created by `seed_library`):

| Role      | Email                 | Password     |
|-----------|-----------------------|--------------|
| Librarian | librarian@library.com | librarian123 |
| Reader    | reader@library.com    | reader123    |

### Pages
| URL | Who | What |
|-----|-----|------|
| `/` | everyone | home page |
| `/auth/register/` | guest | sign up as a reader or a librarian |
| `/auth/login/`, `/auth/logout/` | guest / authorized | log in, log out |
| `/books/` | reader, librarian | all books + filters (title, author, description, available, sort) |
| `/books/<id>/` | reader, librarian | book page; reader can order it, librarian sees who has it |
| `/books/new/` | librarian | add a book |
| `/books/user/<id>/` | librarian | all books provided to a user |
| `/users/`, `/users/<id>/` | librarian | all users, user profile |
| `/orders/` | librarian | all orders, filter by status, close an order |
| `/orders/my/` | reader | my orders |
| `/orders/create/` (POST) | reader | create an order |
| `/authors/` | librarian | all authors, add an author, remove an author without books |

In the View/Template sprint only HTML forms were used; in the Django Forms sprint they were replaced with Django forms (see below).

### Tests
```commandline
python manage.py test
```

Screenshots are in the `screenshots` folder.

---

## Admin panel (Django Admin sprint)

```commandline
cd library
python manage.py migrate
python manage.py seed_library
python manage.py createsuperuser      # user with administrator rights
python manage.py runserver
```
Open http://127.0.0.1:8000/admin/ and log in with the superuser email and password.

What is configured (`*/admin.py`):

* **Users** – custom add/change forms (password is hashed), list with role / active / staff / superuser
  columns, filters by role and status, search by ID, email and name, books issued to the user (inline),
  permissions section for creating an additional staff user with limited rights.
* **Books** – list with ID, title, authors, year, copies, issued now, free copies and last date of issue;
  filters by author, first letter of the title, availability and year; search by book ID, title or author.
  Detail page is split into **Permanent information** (title, authors, year of publication, description)
  and **Changing information** (copies, issued now, free copies, last date of issue, who has the book)
  plus the table of all issues of the book (date of issue and return).
* **Authors** – list with the number of books and titles, filters "has books" and by book, search;
  detail page with personal information, book selector and a table with the author's books.
* **Orders** – list with book ID, title, author, reader, dates and status; filters by status, **book id**,
  **book title**, **book author** and date of issue; search; action "Close selected orders".

Screenshots of the admin panel are in `screenshots/admin`.


---

## Django Forms sprint

All adding/editing pages now use **Django forms** (`*/forms.py`). Every view works the same way:
**GET** – show an empty or pre-filled form, **POST** – validate it with `form.is_valid()`,
save and redirect, or show the same page with the errors under the fields.

| Form | File | Page | Who |
|------|------|------|-----|
| `RegisterForm` | `authentication/forms.py` | `/auth/register/` | guest |
| `LoginForm` | `authentication/forms.py` | `/auth/login/` | guest |
| `ProfileForm` | `authentication/forms.py` | `/auth/profile/` – edit my name | any user |
| `UserEditForm` | `authentication/forms.py` | `/users/<id>/edit/` – edit name, role, activity | librarian |
| `BookForm` | `book/forms.py` | `/books/new/`, `/books/<id>/edit/` – add / edit a book with authors | librarian |
| `BookFilterForm` (GET) | `book/forms.py` | `/books/` – filters | everyone |
| `AuthorForm` | `author/forms.py` | `/authors/` (add), `/authors/<id>/edit/` | librarian |
| `OrderCreateForm` | `order/forms.py` | book page – order a book | reader |
| `OrderExtendForm` | `order/forms.py` | `/orders/<id>/extend/` – change return date | reader |
| `OrderEditForm` | `order/forms.py` | `/orders/<id>/edit/` – edit dates of an order | librarian |

Validation examples: unique email, matching passwords, a book year not in the future, number of copies
not less than the copies issued right now, no duplicate authors, return date within 60 days.

Fields are rendered with one shared template `templates/includes/field.html`.
Screenshots: `screenshots/forms`.

---

## Django REST Framework sprint

REST API is in the `library/api` app (`serializers.py`, `views.py`, `permissions.py`, `urls.py`, `tests.py`).
The trailing slash is optional (`/api/v1/book` and `/api/v1/book/` both work).

| Resource | GET (list / one) | POST | PUT / PATCH | DELETE |
|----------|------------------|------|-------------|--------|
| `/api/v1/user/{id}` | ✔ | ✔ | ✔ | ✔ |
| `/api/v1/user/{id}/order/{id}` | ✔ | ✔ | ✔ | ✔ |
| `/api/v1/order/{id}` | ✔ | ✔ | ✔ | ✔ |
| `/api/v1/book/{id}` | ✔ (filters `?name=`, `?author=`, `?year=`) | ✔ | ✔ | ✔ |
| `/api/v1/author/{id}` | ✔ | ✔ | ✔ | ✔ (only without books) |

**Authentication:** Basic Auth (in Postman: *Authorization → Basic Auth*) or the site session
(log in on the site and open http://127.0.0.1:8000/api/v1/ – the browsable API).

**Permissions:**
* librarian – full access to everything;
* reader – reads books and authors, sees and edits only himself, sees only his orders and can create an order for himself;
* anonymous – `401 Unauthorized`.

**Validation:** unique email, password is hashed, book year not in the future, number of copies not less
than issued copies, no order when there are no free copies, return date later than the date of issue,
an author with books cannot be removed.

Example request body for `POST /api/v1/order/`:
```json
{"user": 2, "book": 9, "plated_end_at": "2026-12-01T18:00:00+02:00"}
```

### Postman
1. `python manage.py seed_library` and `python manage.py runserver`.
2. Postman → **Import** → `postman/Library_API.postman_collection.json`.
3. Open any request and press **Send**, or run the whole collection: **⋯ → Run collection → Run**.
   Every request checks its status code (44 requests, 44 checks – see `postman/newman_report.txt`).

Run the API tests: `python manage.py test api`.

---

## Selenium sprint – login test

`library/selenium_tests/test_login.py` – a Selenium test that opens a real browser (Google Chrome) and checks
logging in with correct and incorrect credentials.

**Test case `test_login_logout_and_invalid_login`:**

| # | Step | Check |
|---|------|-------|
| 1 | Open the homepage | the "Log in" button is shown, nobody is logged in |
| 2 | Click "Log in" in the top right corner | the login page is opened |
| 3–4 | Enter a valid email and password, click "Log in" | – |
| 5 | Verify the login | the user name and "Log out" are in the header, message "Hello, Andrii!", page `/books/` |
| 6 | Click "Log out" in the top right corner | – |
| 7 | Verify the logout | message "You have been logged out.", "Log in" is shown, `/books/` redirects to the login page |
| 8–9 | Enter an invalid email and password, click "Log in" | – |
| 10 | Verify the error | message "Wrong email or password.", the user is still not logged in |

Additional tests: valid email + wrong password, empty fields, deactivated account.
The valid user account is created automatically in a separate test database.

**Run** (Google Chrome must be installed; Selenium downloads the matching ChromeDriver itself):
```commandline
pip install -r requirements.txt
cd library
python manage.py test selenium_tests
```
Options (PowerShell):
```powershell
$env:SELENIUM_PAUSE="2"         # slower steps, good for a video (default 1 second)
$env:SELENIUM_SCREENSHOTS="1"   # save a screenshot of every step to screenshots/selenium
$env:SELENIUM_HEADLESS="1"      # run without a browser window
$env:SELENIUM_BROWSER="edge"    # use Microsoft Edge instead of Chrome
```
Screenshots of the steps: `screenshots/selenium`.
