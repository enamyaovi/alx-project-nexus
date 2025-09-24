import requests
from requests.exceptions import RequestException
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Genre


class Command(BaseCommand):
    """
    Django management command to sync movie genres from TMDB API
    into the local database. Existing genres are updated, and
    new ones are created if they don't already exist.
    """

    GENRES_URL = "https://api.themoviedb.org/3/genre/movie/list"

    help = "Sync genres from TMDB into the database."

    def add_arguments(self, parser):
        """
        Add optional command arguments.
        """
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the sync without writing to the database.",
        )

    def handle(self, *args, **kwargs) -> None:
        """
        Fetch genres from TMDB API and update/create them in the database.
        """
        dry_run = kwargs.get("dry_run", False)

        headers = {
            "Authorization": f"Bearer {settings.TMDB_API_KEY}",
            "accept": "application/json",
        }

        try:
            response = requests.get(self.GENRES_URL, headers=headers, timeout=10)
            response.raise_for_status()
        except RequestException as exc:
            self.stderr.write(self.style.ERROR(f"Failed to fetch genres: {exc}"))
            return

        data = response.json()
        genres = data.get("genres", [])
        created_count, updated_count = 0, 0

        for genre in genres:
            if dry_run:
                self.stdout.write(self.style.NOTICE(
                    f"[Dry Run] Would {'create' if not Genre.objects.filter(id=genre['id']).exists() else 'update'} genre: {genre['name']}"
                ))
                continue

            obj, created = Genre.objects.update_or_create(
                id=genre["id"],
                defaults={"name": genre["name"]},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} genre: {obj.name}"
            ))

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync complete — {created_count} created, {updated_count} updated."
                )
            )
        else:
            self.stdout.write(self.style.NOTICE("Dry run complete — no changes written."))