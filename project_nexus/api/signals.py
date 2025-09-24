from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from api.models import UserProfile

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