from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from core.pagination import paginate

from .models import CurrentAffair


def list_view(request):
    category = request.GET.get('category')
    query = request.GET.get('q', '').strip()

    affairs = CurrentAffair.objects.published()
    if category:
        affairs = affairs.filter(category=category)
    if query:
        affairs = affairs.filter(Q(title__icontains=query) | Q(content__icontains=query))

    page_obj = paginate(request, affairs, per_page=10)
    return render(request, 'current_affairs/list.html', {
        'page_obj': page_obj,
        'affairs': page_obj.object_list,
        'categories': CurrentAffair.Category.choices,
        'selected_category': category,
        'query': query,
    })


def detail(request, pk):
    affair = get_object_or_404(CurrentAffair.objects.published(), pk=pk)
    return render(request, 'current_affairs/detail.html', {'affair': affair})
