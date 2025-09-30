from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import UserProfile

from api.utils import send_account_activation_email

User = get_user_model()


@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    """
    Ensure that each User has a corresponding UserProfile.
    Creates a profile when a new User is registered,
    and saves updates when the User instance is saved.
    """
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, "profile"):
            instance.profile.save()


@receiver(post_save, sender=User)
def send_email_confirmation_link_signal(sender, instance, created, **kwargs):
    """
    Sends a welcome and confirmation email to activate user's account
    """
    if created:
        send_account_activation_email(instance)