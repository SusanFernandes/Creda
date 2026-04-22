"""
Auth views — all async (Issue 8).
Login, register, logout, landing. On register/login, also register with FastAPI and store JWT in session.
"""
import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import login as _django_login, logout as _django_logout
from django.shortcuts import redirect, render

django_login = sync_to_async(_django_login)
django_logout = sync_to_async(_django_logout)

from accounts.models import User


async def landing_view(request):
    """Public landing page — redirect to dashboard if already logged in."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


async def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = ""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        try:
            user = await User.objects.aget(email=email)
            if user.check_password(password):
                await django_login(request, user)
                # Get JWT from FastAPI
                jwt_token = await _get_backend_jwt(email, password)
                if jwt_token:
                    request.session["backend_jwt"] = jwt_token
                return redirect("dashboard")
            else:
                error = "Invalid password"
        except User.DoesNotExist:
            error = "No account with this email"

    return render(request, "accounts/login.html", {"error": error})


async def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = ""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        name = request.POST.get("name", "").strip()

        if await User.objects.filter(email=email).aexists():
            error = "Email already registered"
        elif len(password) < 8:
            error = "Password must be at least 8 characters"
        else:
            # Register with FastAPI backend FIRST (atomic: don't create Django user if backend fails)
            jwt_token = await _register_backend(email, password, name)
            if jwt_token is None:
                error = "Registration failed — please try again"
            else:
                user = User(username=email, email=email, first_name=name)
                user.set_password(password)
                await user.asave()
                await django_login(request, user)
                request.session["backend_jwt"] = jwt_token
                return redirect("dashboard")

    return render(request, "accounts/register.html", {"error": error})


async def logout_view(request):
    await django_logout(request)
    return redirect("landing")


async def _get_backend_jwt(email: str, password: str) -> str | None:
    """Get JWT token from FastAPI backend."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_API_URL}/auth/token",
                json={"email": email, "password": password},
            )
            if resp.status_code == 200:
                return resp.json().get("token")
    except Exception:
        pass
    return None


async def _register_backend(email: str, password: str, name: str) -> str | None:
    """Register user on FastAPI backend and return JWT."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_API_URL}/auth/register",
                json={"email": email, "password": password, "name": name},
            )
            if resp.status_code == 200:
                return resp.json().get("token")
    except Exception:
        pass
    return None
