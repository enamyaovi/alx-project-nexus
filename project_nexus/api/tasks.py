from celery import shared_task
from django.core.mail import EmailMessage


@shared_task
def send_email_service(email_address, subject, message):

    email_service = EmailMessage(
        subject,
        to=(email_address,),
        body=message
    )

    email_service.send(fail_silently=False)
    print('Sent with celery')