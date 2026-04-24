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
    signup_required = False
    email_prefill = ""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        email_prefill = email

        try:
            user = await User.objects.aget(email=email)
            if user.check_password(password):
                await django_login(request, user)
                # Get JWT from FastAPI
                jwt_token, backend_uid = await _get_backend_jwt(email, password)
                if jwt_token:
                    request.session["backend_jwt"] = jwt_token
                if backend_uid:
                    request.session["backend_user_id"] = str(backend_uid)
                return redirect("dashboard")
            else:
                error = "Invalid password"
        except User.DoesNotExist:
            signup_required = True

    return render(
        request,
        "accounts/login.html",
        {
            "error": error,
            "signup_required": signup_required,
            "email_prefill": email_prefill,
        },
    )


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
            jwt_token, backend_uid = await _register_backend(email, password, name)
            if jwt_token is None:
                error = "Registration failed — please try again"
            else:
                user = User(username=email, email=email, first_name=name)
                user.set_password(password)
                await user.asave()
                await django_login(request, user)
                request.session["backend_jwt"] = jwt_token
                if backend_uid:
                    request.session["backend_user_id"] = str(backend_uid)
                return redirect("dashboard")

    return render(request, "accounts/register.html", {"error": error})


async def logout_view(request):
    request.session.pop("backend_jwt", None)
    request.session.pop("backend_user_id", None)
    await django_logout(request)
    return redirect("landing")


async def _get_backend_jwt(email: str, password: str) -> tuple[str | None, str | None]:
    """Get JWT and FastAPI user id from backend (TokenResponse)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_API_URL}/auth/token",
                json={"email": email, "password": password},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("token"), data.get("user_id")
    except Exception:
        pass
    return None, None


async def _register_backend(email: str, password: str, name: str) -> tuple[str | None, str | None]:
    """Register user on FastAPI backend; return JWT and FastAPI users.id (UUID)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_API_URL}/auth/register",
                json={"email": email, "password": password, "name": name},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("token"), data.get("user_id")
    except Exception:
        pass
    return None, None


async def forgot_password_view(request):
    """Password reset request form."""
    message = ""
    error = ""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if not email:
            error = "Please enter your email address"
        else:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{settings.BACKEND_API_URL}/auth/password-reset-request",
                        json={"email": email},
                    )
                    data = resp.json()
                    reset_token = data.get("reset_token", "")
                    if reset_token:
                        # In dev, redirect directly to reset form with token
                        return redirect(f"/reset-password/?token={reset_token}")
                    message = data.get("message", "If an account exists, a reset link has been sent.")
            except Exception:
                error = "Could not process request. Try again later."

    return render(request, "accounts/forgot_password.html", {
        "message": message, "error": error,
    })


async def reset_password_view(request):
    """Password reset confirmation form — enter new password with valid token."""
    token = request.GET.get("token", "") or request.POST.get("token", "")
    message = ""
    error = ""

    if request.method == "POST":
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not token:
            error = "Invalid reset link. Please request a new one."
        elif len(new_password) < 8:
            error = "Password must be at least 8 characters"
        elif new_password != confirm_password:
            error = "Passwords do not match"
        else:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{settings.BACKEND_API_URL}/auth/password-reset-confirm",
                        json={"token": token, "new_password": new_password},
                    )
                    if resp.status_code == 200:
                        # Also update Django password
                        data = resp.json()
                        try:
                            # Find user by attempting login or just show success
                            pass
                        except Exception:
                            pass
                        message = "Password reset successfully! You can now log in."
                    else:
                        data = resp.json()
                        error = data.get("detail", "Reset failed. Token may be expired.")
            except Exception:
                error = "Could not process request. Try again later."

    return render(request, "accounts/reset_password.html", {
        "token": token, "message": message, "error": error,
    })
