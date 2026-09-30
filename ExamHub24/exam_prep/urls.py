from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # powers the language switcher (navbar.html)
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('exams/', include('exams.urls')),
    path('mock-tests/', include('mock_tests.urls')),
    path('results/', include('results.urls')),
    path('current-affairs/', include('current_affairs.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    path('payments/', include('payments.urls')),
    path('study-material/', include('study_material.urls')),
    path('notifications/', include('notifications.urls')),
    path('questions/', include('questions.urls')),
    path('discussion/', include('discussion.urls')),
    path('institutions/', include('institutions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
