from django.contrib.auth import authenticate, login

from rest_framework import status, viewsets
from rest_framework.response import Response

from utils.decorators import check_authentication, handle_exceptions

from .models import User
from .serializers import UserSerializer


def _ok(data, code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None,
        },
        status=code,
    )


def _fail(error, code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": None,
            "error": error,
        },
        status=code,
    )


class SignupViewSet(viewsets.ViewSet):
    """POST /user-api/signup/  {email, password, full_name}"""

    @handle_exceptions
    def create(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        full_name = (request.data.get("full_name") or "").strip()

        if not email or not password:
            return _fail("Email and password are required.")

        if len(password) < 6:
            return _fail("Password must be at least 6 characters long.")

        if User.objects.filter(email=email).exists():
            return _fail("An account with this email already exists.")

        user = User.objects.create_user(email=email, password=password, full_name=full_name)
        login(request, user)

        return _ok(UserSerializer(user).data, status.HTTP_201_CREATED)


class AuthViewSet(viewsets.ViewSet):
    """
    POST /user-api/auth/  {email, password}  -> log in, start a session
    GET  /user-api/auth/                     -> current logged-in user
    """

    @handle_exceptions
    def create(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""

        if not email or not password:
            return _fail("Email and password are required.")

        user = authenticate(request, username=email, password=password)
        if user is None:
            return _fail("Invalid email or password.")

        if not user.is_active:
            return _fail("This account has been deactivated.")

        login(request, user)
        return _ok(UserSerializer(user).data)

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return _ok(UserSerializer(request.user).data)
