from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import render

from apps.todos.views import dashboard


def home(request) -> HttpResponse:
    if request.user.is_authenticated:
        return dashboard(request)
    return render(request, "web/landing_page.html")


@user_passes_test(lambda u: u.is_superuser)
def simulate_error(request) -> HttpResponse:
    raise RuntimeError("This is a simulated error.")
