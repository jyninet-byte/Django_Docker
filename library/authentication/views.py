from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from author.models import Author
from book.models import Book
from order.models import Order

from .decorators import librarian_required
from .forms import LoginForm, ProfileForm, RegisterForm, UserEditForm
from .models import ROLE_CHOICES, CustomUser


def home(request):
    """Landing page with a short overview of the library."""
    context = {
        'books_count': Book.objects.count(),
        'authors_count': Author.objects.count(),
        'open_orders_count': Order.objects.filter(end_at__isnull=True).count(),
        'latest_books': Book.objects.order_by('-id')[:4],
    }
    return render(request, 'home.html', context)


def register(request):
    """GET: empty registration form. POST: validate it and create the user."""
    if request.user.is_authenticated:
        return redirect('book_list')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')
            return redirect('book_list')
    else:
        form = RegisterForm()
    return render(request, 'authentication/register.html', {'form': form})


def login_view(request):
    """GET: login form. POST: check email and password."""
    if request.user.is_authenticated:
        return redirect('book_list')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.user)
            messages.success(request, f'Hello, {form.user.first_name or form.user.email}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('book_list')
    else:
        form = LoginForm(request)
    return render(request, 'authentication/login.html', {'form': form, 'next': request.GET.get('next', '')})


@login_required
def profile_edit(request):
    """GET: form with the current user's data. POST: save the changes."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile_edit')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'authentication/profile_form.html', {'form': form})


@require_POST
def logout_view(request):
    """Log out the current user."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@librarian_required
def user_list(request):
    """Show all users with search and role filter (librarian only)."""
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '')

    users = CustomUser.objects.annotate(
        open_orders=Count('order', filter=Q(order__end_at__isnull=True)),
        total_orders=Count('order'),
    )
    if query:
        users = users.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query)
                             | Q(middle_name__icontains=query) | Q(email__icontains=query))
    if role in ('0', '1'):
        users = users.filter(role=int(role))

    return render(request, 'authentication/user_list.html',
                  {'users': users, 'query': query, 'role': role, 'roles': ROLE_CHOICES})


@librarian_required
def user_detail(request, user_id):
    """Show a specific user (librarian only)."""
    user = get_object_or_404(CustomUser, pk=user_id)
    orders = Order.objects.filter(user=user).select_related('book')
    context = {
        'profile': user,
        'open_orders': orders.filter(end_at__isnull=True),
        'closed_count': orders.filter(end_at__isnull=False).count(),
    }
    return render(request, 'authentication/user_detail.html', context)


@librarian_required
def user_edit(request, user_id):
    """GET: form with the user's data. POST: save the changes (librarian only)."""
    user = get_object_or_404(CustomUser, pk=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            if user == request.user and (not form.cleaned_data['is_active'] or form.cleaned_data['role'] != 1):
                form.add_error(None, 'You cannot deactivate yourself or remove your own librarian role.')
            else:
                form.save()
                messages.success(request, f'User {user.full_name} has been updated.')
                return redirect('user_detail', user_id=user.id)
    else:
        form = UserEditForm(instance=user)
    return render(request, 'authentication/user_form.html', {'form': form, 'profile': user})
