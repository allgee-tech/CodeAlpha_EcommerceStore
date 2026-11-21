from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cart.services import merge_session_cart
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import CustomerProfile

def login_view(request):
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        merge_session_cart(request.user, request.session)
        messages.success(request, "Welcome back to NOVA MARKET.")
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)
        return redirect("store:home")
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})

def register_view(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            CustomerProfile.objects.create(user=user)
            login(request, user)
            merge_session_cart(user, request.session)
        messages.success(request, "Your NOVA MARKET account is ready.")
        return redirect("store:home")
    return render(request, "accounts/register.html", {"form": form})

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been safely signed out.")
    return redirect("store:home")

@login_required
def dashboard(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    profile_form = ProfileForm(request.POST or None, instance=profile, prefix="profile")
    password_form = PasswordChangeForm(request.user, request.POST or None, prefix="password")
    if request.method == "POST":
        form_name = request.POST.get("form_name")
        if form_name == "profile" and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your account details have been updated.")
            return redirect("accounts:dashboard")
        if form_name == "password" and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed securely.")
            return redirect("accounts:dashboard")
    return render(request, "accounts/dashboard.html", {"profile_form": profile_form, "password_form": password_form})
