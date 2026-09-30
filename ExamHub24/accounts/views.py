from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone

from core.throttle import rate_limit

from .forms import OTPForm, ProfileForm, RegistrationForm, StudentProfileForm
from .models import OTPVerification, StudentProfile, User


def _send_otp_email(user, otp):
    send_mail(
        subject='ExamHub24 — Verify your account',
        message=f'Your OTP is {otp.otp_code}. It is valid for {settings.OTP_VALIDITY_MINUTES} minutes.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


@rate_limit('register', max_attempts=10, window_seconds=600)
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile, _ = StudentProfile.objects.get_or_create(user=user)

            referral_code = (form.cleaned_data.get('referral_code') or '').strip().upper()
            if referral_code:
                referrer_profile = StudentProfile.objects.filter(referral_code=referral_code).exclude(user=user).first()
                if referrer_profile:
                    profile.referred_by = referrer_profile.user
                    profile.save(update_fields=['referred_by'])
                else:
                    messages.warning(request, f'Referral code "{referral_code}" was not recognized — continuing without it.')

            institution_code = (form.cleaned_data.get('institution_code') or '').strip().upper()
            if institution_code:
                from institutions.models import Institution
                institution = Institution.objects.filter(code=institution_code, is_active=True).first()
                if institution and institution.has_capacity():
                    profile.institution = institution
                    profile.save(update_fields=['institution'])
                elif institution:
                    messages.warning(request, f'"{institution.name}" has reached its student limit — continuing without linking your account to them.')
                else:
                    messages.warning(request, f'Institution code "{institution_code}" was not recognized — continuing without it.')

            otp = OTPVerification.objects.create(
                user=user,
                purpose=OTPVerification.Purpose.REGISTRATION,
                expires_at=timezone.now() + timedelta(minutes=settings.OTP_VALIDITY_MINUTES),
            )
            _send_otp_email(user, otp)
            request.session['pending_verification_user_id'] = user.id
            messages.info(request, 'Account created! Please verify the OTP sent to your email.')
            return redirect('accounts:verify_otp')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@rate_limit('verify_otp', max_attempts=10, window_seconds=600)
def verify_otp(request):
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        return redirect('accounts:register')
    user = User.objects.filter(id=user_id).first()
    if not user:
        return redirect('accounts:register')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['otp_code']
            otp = (
                OTPVerification.objects.filter(user=user, purpose=OTPVerification.Purpose.REGISTRATION, is_used=False)
                .order_by('-created_at')
                .first()
            )
            if otp and otp.otp_code == code and otp.is_valid():
                otp.is_used = True
                otp.save(update_fields=['is_used'])
                user.is_verified = True
                user.save(update_fields=['is_verified'])

                from subscriptions.services import REFERRAL_BONUS_DAYS, grant_referral_reward
                if grant_referral_reward(user):
                    messages.info(request, f'You and your referrer each received {REFERRAL_BONUS_DAYS} days of free premium access!')

                del request.session['pending_verification_user_id']
                auth_login(request, user)
                messages.success(request, 'Account verified successfully! Welcome to ExamHub24.')
                return redirect('dashboard:home')

            if otp and not otp.is_valid() and otp.attempts >= OTPVerification.MAX_ATTEMPTS:
                messages.error(request, 'Too many incorrect attempts. Please request a new OTP.')
            elif otp:
                otp.register_failed_attempt()
                messages.error(request, 'Invalid or expired OTP. Please try again.')
            else:
                messages.error(request, 'No active OTP found. Please request a new one.')
    else:
        form = OTPForm()
    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': user.email})


@rate_limit('resend_otp', max_attempts=5, window_seconds=600)
def resend_otp(request):
    """Allows a not-yet-verified user to request a fresh OTP (e.g. after the old one expired or locked out)."""
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        return redirect('accounts:register')
    user = User.objects.filter(id=user_id).first()
    if not user or user.is_verified:
        return redirect('accounts:register')

    otp = OTPVerification.objects.create(
        user=user,
        purpose=OTPVerification.Purpose.REGISTRATION,
        expires_at=timezone.now() + timedelta(minutes=settings.OTP_VALIDITY_MINUTES),
    )
    _send_otp_email(user, otp)
    messages.success(request, 'A new OTP has been sent to your email.')
    return redirect('accounts:verify_otp')


class ExamHubLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


def logout_view(request):
    auth_logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:home')


@login_required
def profile(request):
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = ProfileForm(request.POST, request.FILES, instance=request.user)
        profile_form = StudentProfileForm(request.POST, instance=student_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        user_form = ProfileForm(instance=request.user)
        profile_form = StudentProfileForm(instance=student_profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'student_profile': student_profile,
        'administered_institutions': request.user.administered_institutions.all(),
        'is_affiliate': hasattr(request.user, 'affiliate_profile'),
    })
