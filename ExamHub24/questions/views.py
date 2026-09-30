import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.pagination import paginate
from exams.models import Subject

from .models import BookmarkedQuestion, Question


@login_required
@require_POST
def bookmark_toggle(request, question_id):
    """AJAX endpoint used on the result/solutions page — toggles a bookmark on/off."""
    question = get_object_or_404(Question, pk=question_id)
    bookmark = BookmarkedQuestion.objects.filter(user=request.user, question=question).first()
    if bookmark:
        bookmark.delete()
        bookmarked = False
    else:
        BookmarkedQuestion.objects.create(user=request.user, question=question)
        bookmarked = True
    return JsonResponse({'bookmarked': bookmarked})


@login_required
def bookmark_list(request):
    bookmarks = BookmarkedQuestion.objects.filter(user=request.user).select_related('question', 'question__subject')
    page_obj = paginate(request, bookmarks, per_page=20)
    return render(request, 'questions/bookmark_list.html', {'page_obj': page_obj, 'bookmarks': page_obj.object_list})


@login_required
def practice_subject_list(request):
    """Landing page for Practice Mode — pick a subject to practice, no timer, instant feedback."""
    subjects = Subject.objects.select_related('exam').all()
    return render(request, 'questions/practice_subject_list.html', {'subjects': subjects})


@login_required
def practice_session(request, subject_id):
    """
    One question at a time, no timer, no scoring/leaderboard impact — purely for
    self-practice. On submit, shows correct/incorrect + explanation immediately, then
    lets the student move to another random question from the same subject.
    """
    subject = get_object_or_404(Subject, pk=subject_id)
    feedback = None
    question = None

    if request.method == 'POST':
        question = get_object_or_404(Question, pk=request.POST.get('question_id'), subject=subject)
        selected = request.POST.get('selected_option')
        feedback = {
            'selected': selected,
            'is_correct': question.check_answer(selected) if selected else None,
        }
    else:
        question_pool = list(Question.objects.filter(subject=subject, is_active=True).values_list('id', flat=True))
        if question_pool:
            question = Question.objects.get(pk=random.choice(question_pool))

    is_bookmarked = (
        question is not None and request.user.is_authenticated
        and BookmarkedQuestion.objects.filter(user=request.user, question=question).exists()
    )

    return render(request, 'questions/practice_session.html', {
        'subject': subject,
        'question': question,
        'feedback': feedback,
        'is_bookmarked': is_bookmarked,
    })
