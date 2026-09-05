from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from core.forms import RegisterForm
from django.contrib.auth import get_user_model
from accounts.decorators import vendor_required
from stores.models import Store
from products.models import Product
from orders.models import Order, OrderItem
from core.models import Notification, UserInteraction, SearchQuery


from .forms import UserEditForm


User = get_user_model()


@login_required
def edit_profile(request):
    """View for editing user profile information."""
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserEditForm(instance=request.user)
    
    return render(request, 'user/edit_profile.html', {'form': form})


def register(request):
    """Registration view using project RegisterForm (includes user_type)."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = None
            try:
                user = User.objects.create_user(
                    username=data.get('username'),
                    email=data.get('email'),
                    password=data.get('password1')
                )
                # set user_type if available on model
                if hasattr(user, 'user_type'):
                    user.user_type = data.get('user_type', 'customer')
                    user.save()
                login(request, user)
                messages.success(request, 'Registration successful. Welcome!')
                if getattr(user, 'user_type', None) == 'vendor':
                    return redirect('vendor:dashboard')
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Error creating account: {e}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    # Use the project's `register.html` template which renders all form fields
    return render(request, 'register.html', {'form': form})


@login_required
@vendor_required
def vendor_dashboard(request):
    # redirect to vendor_panel namespaced dashboard (primary implementation lives there)
    return redirect('vendor:dashboard')


@login_required
def profile(request):
    """User profile page where users can view and edit basic info."""
    user = request.user
    return render(request, 'user/profile.html', {'user_profile': user})


@login_required
def overview(request):
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-created_at')[:20]
    recent_items = OrderItem.objects.filter(order__user=user).select_related('product', 'service', 'order').order_by('-order__created_at')[:10]
    notifications = Notification.objects.filter(user=user).order_by('-created_at')[:10]
    interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')[:20]
    searches = SearchQuery.objects.filter(user=user).order_by('-created_at')[:10]
    return render(request, 'user/overview.html', {
        'user_profile': user,
        'orders': orders,
        'recent_items': recent_items,
        'notifications': notifications,
        'interactions': interactions,
        'searches': searches,
    })


@login_required
def favorites(request):
    """Show user's favorite stores (uses FavoriteStore model if available)."""
    try:
        from stores.models import FavoriteStore
        favs = FavoriteStore.objects.filter(user=request.user).select_related('store')
    except Exception:
        favs = []
    return render(request, 'user/favorites.html', {'favorites': favs})


@login_required
def notifications(request):
    """User notifications page scoped to current account."""
    items = Notification.objects.filter(user=request.user).order_by('-created_at')[:200]
    return render(request, 'user/notifications.html', {'notifications': items})
