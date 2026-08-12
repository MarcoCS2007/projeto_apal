from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    if request.htmx:
        return HttpResponse("<span>Olá, mundo! (via HTMX)</span>")
    return render(request, "index.html")
