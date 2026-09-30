from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.pagination import paginate

from .models import Notification


@login_required
def list_view(request):
    notifications = Notification.objects.filter(user=request.user)
    page_obj = paginate(request, notifications, per_page=20)
    # Mark only the notifications shown on this page as read.
    Notification.objects.filter(pk__in=[n.pk for n in page_obj.object_list], is_read=False).update(is_read=True)
    return render(request, 'notifications/list.html', {'page_obj': page_obj, 'notifications': page_obj.object_list})


@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('notifications:list')
