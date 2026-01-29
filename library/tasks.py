from celery import shared_task
from .models import Loan
from django.core.mail import send_mail
from django.conf import settings
from celery.schedules import crontab
from library_system.celery import app
from datetime import date, timedelta

@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Loan.DoesNotExist:
        pass

@shared_task
def check_overdue_loans():
    overdue_loans = Loan.objects.select_related('book', 'member__user').filter(is_returned=False, due_date__gt=date.today())
    for overdue_loan in overdue_loans:
        member_email = overdue_loan.member.user.email
        member_name = overdue_loan.member.user.get_full_name()
        book_title = overdue_loan.book.title

        send_mail(
            subject='Book Loan Overdue',
            message=f'Hello {member_name},\n\nYou loaned book with title: "{book_title}" is overdue.\nPlease return it.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )

app.conf.beat_schedule={
    'send_overdue_loan_notice' : {
        'task': 'check_overdue_loans',
        'schedule': crontab(hour=9, minute=0)
    }
}