from django.http import Http404
from django.urls import reverse

class RestrictStaffToAdminMiddleware(object):
    """
    A middleware that restricts non-staff members access to administration panels.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is going to the admin site
        if request.path.startswith(reverse("admin:index")):
            # If the user is logged in BUT is not a staff member, pretend the page doesn't exist
            if request.user.is_authenticated and not request.user.is_staff:
                raise Http404

            # If the user is completely unauthenticated, we let the request pass.
            # Django's default admin behavior will automatically redirect them to the admin login page.

        return self.get_response(request)
