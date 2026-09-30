from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.throttle import rate_limit
from questions.models import Question

from .models import Discussion


def question_discussion(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    threads = (
        Discussion.objects.filter(question=question, parent__isnull=True)
        .select_related('user')
        .prefetch_related('replies__user', 'likes')
    )
    return render(request, 'discussion/thread.html', {'question': question, 'threads': threads})


@login_required
@rate_limit('post_comment', max_attempts=20, window_seconds=600)
def post_comment(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    if request.method == 'POST':
        comment_text = (request.POST.get('comment') or '').strip()
        parent_id = request.POST.get('parent_id')

        if not comment_text:
            pass  # silently ignore empty submissions rather than erroring
        elif len(comment_text) > 2000:
            pass  # ignore absurdly long submissions (matches model's max_length)
        else:
            parent = Discussion.objects.filter(pk=parent_id, question=question).first() if parent_id else None
            Discussion.objects.create(question=question, user=request.user, comment=comment_text, parent=parent)

    # Redirect back to wherever the discussion widget was shown (result page, practice
    # mode, etc.) so this works as a plain HTML form without needing JS/AJAX.
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('discussion:question_discussion', question_id=question.id)


@login_required
@require_POST
def toggle_like(request, discussion_id):
    comment = get_object_or_404(Discussion, pk=discussion_id)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'like_count': comment.like_count})


@login_required
@require_POST
def flag_comment(request, discussion_id):
    """Lets any student flag an inappropriate comment for admin review (visible in the admin panel)."""
    comment = get_object_or_404(Discussion, pk=discussion_id)
    comment.is_flagged = True
    comment.save(update_fields=['is_flagged'])
    return JsonResponse({'flagged': True})
