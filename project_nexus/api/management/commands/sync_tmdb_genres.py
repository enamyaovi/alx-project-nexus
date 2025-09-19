import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Genre  # adjust to your app name

class Command(BaseCommand):
    help = "Sync genres from TMDB into the database."

    def handle(self, *args, **kwargs):
        url = "https://api.themoviedb.org/3/genre/movie/list"
        headers = {
            "Authorization": f"Bearer {settings.TMDB_API_KEY}",
            "accept": "application/json",
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.stderr.write(self.style.ERROR(
                f"Failed to fetch genres: {response.status_code} {response.text}"
            ))
            return

        data = response.json()
        genres = data.get("genres", [])
        for genre in genres:
            obj, created = Genre.objects.update_or_create(
                id=genre["id"],
                defaults={"name": genre["name"]}
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} genre: {obj.name}"))
