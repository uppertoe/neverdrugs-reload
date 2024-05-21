from django.shortcuts import render
from django.http import HttpResponseNotAllowed
import logging

from .models.search import SearchIndex

logger = logging.getLogger(__name__)

def search(request):
    # Only handle GET requests
    if request.method != "GET":
        return HttpResponseNotAllowed(['GET'])

    # Get the search query and results
    query = request.GET.get('q')
    results = SearchIndex.search(query) if query else []

    logger.info(f'Search performed: {query}')

    if request.headers.get('HX-Request'):
        # If the request is an HTMX request, return only the results part
        return render(request, 'search/partials/search_results.html', {'results': results})

    # Assemble the context dictionary
    return render(request, 'search/search_results.html', {'results': results})
