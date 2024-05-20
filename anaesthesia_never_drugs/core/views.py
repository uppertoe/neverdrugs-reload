from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotAllowed

from .tasks import import_who_atc, dispatch_orphanet_imports
from .models.search import SearchIndex


def search(request):
    # Only handle GET requests
    if request.method != "GET":
        return HttpResponseNotAllowed(['GET'])

    # Get the search query and results
    query = request.GET.get('q')
    results = SearchIndex.search(query) if query else []

    if request.headers.get('HX-Request'):
        # If the request is an HTMX request, return only the results part
        return render(request, 'search/partials/search_results.html', {'results': results})

    # Assemble the context dictionary
    return render(request, 'search/search_results.html', {'results': results})
