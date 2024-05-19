from django.shortcuts import render
from django.http import HttpResponse

from .tasks import import_who_atc, dispatch_orphanet_imports


# Create your views here.
def scrape(request):
    import_who_atc.delay()
    return HttpResponse(200)

def scrape_orphanet(request):
    dispatch_orphanet_imports.delay()
    return HttpResponse(200)