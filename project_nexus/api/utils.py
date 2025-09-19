from rest_framework.permissions import BasePermission, SAFE_METHODS
import json
from django.core.cache import cache


#caching utils
def get_or_set_cache(
    key: str, fetch_func, timeout: int = 60 * 60 * 24, *args, **kwargs):

    cached_data = cache.get(key)
    if cached_data:
        try:
            return json.loads(cached_data)
        except (TypeError, json.JSONDecodeError):
            return cached_data 

    # if not in cache, call the fetch function
    fresh_data = fetch_func(*args, **kwargs)

    try:
        cache.set(key, json.dumps(fresh_data), timeout=timeout)
    except TypeError:
        cache.set(key, fresh_data, timeout=timeout)

    return fresh_data


def read_results_json():
    try:
        with open('data.json') as json_file:
            json_data = json.load(json_file)
            return json_data['results']
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []
    except Exception:
        return []


def get_movie_by_id(target_value, results=read_results_json()):
    for item in results:
        if item.get('id') == int(target_value):
            return item
    return None


#permissions
class IsAdminOrAnonymous(BasePermission):
    def has_permission(self, request, view): # type: ignore
        if request.method in SAFE_METHODS:
            return True
        if request.method == 'POST':
            return request.user.is_anonymous or request.user.is_superuser
        return False
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True 
        return request.user.is_anonymous
    

class IsUser(BasePermission):
    """
    Permission to ensure the user is authenticated and is 
    accessing their own object.
    """

    def has_permission(self, request, view):
        """
        Allow access if the user is authenticated.
        """
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Allow access only if the user owns the object.
        """
        return obj == request.user


#pagination
from rest_framework.pagination import PageNumberPagination
class StandardPagination(PageNumberPagination):
    page_size = 5  
    page_size_query_param = "page_size"  
    max_page_size = 50