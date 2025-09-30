import json
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import tokens, get_user_model
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.pagination import PageNumberPagination
from typing import Any, Dict

User = get_user_model()

from api.tasks import send_email_service
# Caching Utilities
def get_or_set_cache(
    key: str,
    fetch_func,
    timeout: int = 60 * 60 * 24,
    serialize: bool = True,
    *args,
    **kwargs,
) -> Any | Dict:
    """
    Retrieve data from cache if available, otherwise call fetch_func,
    cache its result, and return it.

    Args:
        key (str): Cache key.
        fetch_func (callable): Function to fetch data if not in cache.
        timeout (int): Expiration time in seconds.
        serialize (bool): Whether to json.dumps the data before caching.
        *args, **kwargs: Arguments passed to fetch_func.

    Returns:
        Any: Cached or freshly fetched data.
    """
    cached_data = cache.get(key)
    if cached_data:
        if isinstance(cached_data, str):
            try:
                return json.loads(cached_data)
            except (TypeError, json.JSONDecodeError):
                return cached_data
        return cached_data

    # Fetch fresh data
    fresh_data = fetch_func(*args, **kwargs)

    # Cache it
    try:
        if serialize:
            cache.set(key, json.dumps(fresh_data), timeout=timeout)
        else:
            cache.set(key, fresh_data, timeout=timeout)
    except TypeError:
        cache.set(key, fresh_data, timeout=timeout)

    return fresh_data


def read_results_json() -> list[dict]:
    """
    Read and return movie results from a local JSON file.

    Returns:
        list[dict]: List of movie results, or an empty list if errors occur.
    """
    try:
        with open("data.json") as json_file:
            json_data = json.load(json_file)
            return json_data.get("results", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    except Exception:
        return []


def get_movie_by_id_old(
    target_value: int, results: list[dict] | None = None) -> dict | None:
    """
    Find a movie by ID from a given list of results.

    Args:
        target_value (int): The movie ID to search for.
        results (list[dict] | None): List of movie results.

    Returns:
        dict | None: The movie dict if found, otherwise None.
    """
    results = results or read_results_json()
    for item in results:
        if item.get("id") == int(target_value):
            return item
    return None


# Permissions
class IsAdminOrAnonymous(BasePermission):
    """
    Custom permission:
    - Allow safe methods for all.
    - Allow POST for anonymous users or superusers.
    - Deny all other methods.
    """

    def has_permission(self, request, view):  # type: ignore
        if request.method in SAFE_METHODS:
            return True
        if request.method == "POST":
            return request.user.is_anonymous or request.user.is_superuser
        return False

    def has_object_permission(self, request, view, obj):  # type: ignore
        return request.user.is_superuser or request.user.is_anonymous


class IsUser(BasePermission):
    """
    Permission to ensure the user is authenticated and
    accessing their own object.
    """

    def has_permission(self, request, view):  # type: ignore
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):  # type: ignore
        return obj == request.user


# Pagination
class StandardPagination(PageNumberPagination):
    """
    Default pagination for API endpoints.
    Allows client to control page size with ?page_size=,
    but caps maximum size.
    """
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 50


#email utils
def send_account_activation_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = tokens.default_token_generator.make_token(user)

    subject = "Activate Your Account!"
    path = reverse(
        'api:users-activate-account',
        kwargs={'uid': uid, 'token': token}
    )
    activation_link = f"{settings.BASE_URL}{path}"

    message = render_to_string(
        'api/activation_email.txt',
        context={
            'email_activation_link': activation_link,
            'user': user
        }
    )

    send_email_service.delay( # type: ignore
        email_address=user.email,
        subject=subject,
        message=message
    )
