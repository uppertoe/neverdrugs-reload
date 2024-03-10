from django.shortcuts import render
from django.http import HttpResponse

from .tasks import import_who_atc


# Create your views here.
def scrape(request):
    import_who_atc.delay()
    return HttpResponse(200)