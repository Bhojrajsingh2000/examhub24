from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def paginate(request, queryset, per_page=20):
    """Returns a Django Page object for `queryset`, reading the page number from ?page=."""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)
