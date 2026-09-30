from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from exams.models import Subject

from .models import StudyMaterial, VideoLecture


@login_required
def list_view(request):
    subject_id = request.GET.get('subject')
    materials = StudyMaterial.objects.select_related('subject')
    videos = VideoLecture.objects.select_related('subject')
    if subject_id:
        materials = materials.filter(subject_id=subject_id)
        videos = videos.filter(subject_id=subject_id)
    subjects = Subject.objects.all()
    return render(request, 'study_material/list.html', {
        'materials': materials,
        'videos': videos,
        'subjects': subjects,
        'selected_subject': subject_id,
    })


@login_required
def download(request, pk):
    material = get_object_or_404(StudyMaterial, pk=pk)
    if material.is_premium and not request.user.has_active_subscription():
        messages.warning(request, 'This material is available for premium subscribers only.')
        return redirect('subscriptions:plans')
    StudyMaterial.objects.filter(pk=pk).update(download_count=material.download_count + 1)
    return redirect(material.file.url)
