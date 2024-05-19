def chunk_queryset(queryset, chunk_size=100):
    '''
    Given a queryset and a chunk size, returns a generator
    Iterating over this generator gives the next chunk from the queryset

    Each chunk is a list of IDs from the queryset
    '''
    total_count = queryset.count()
    for start in range(0, total_count, chunk_size):
        end = min(start + chunk_size, total_count)
        yield list(queryset[start:end].values_list('id', flat=True))


def chunk_generator(generator, chunk_size=20):
    '''
    Given a generator, yields chunk_size of the underlying objects
    Iterating over this generator gives the next chunk
    '''
    chunk=[]
    for item in generator:
        print(item)
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    # If elements remaining smaller than chunk size
    if chunk:
        yield chunk