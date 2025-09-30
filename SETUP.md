# Project Nexus – Local Development Setup

This guide explains how to run the **Project Nexus Movie Recommendation API** locally for development and testing.

---

## Prerequisites

Make sure you have the following installed:

* [Python 3.10+](https://www.python.org/downloads/)
* [PostgreSQL 14+](https://www.postgresql.org/download/)
* [Redis 7+](https://redis.io/download/)
* [Git](https://git-scm.com/)

> **Note:** PostgreSQL is recommended for production, but SQLite can also be used for local development and quick setup.

---

## 1. Clone the Repository

```bash
git clone https://github.com/<enamyaovi>/project-nexus.git
cd project-nexus
```

---

## 2. Create and Activate Virtual Environment

Using `venv`:

```bash
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Environment Variables

Create a `.env` file in the project root with the following values:

```ini
# General settings
DEBUG=True 
SECRET_KEY=your_secret_key

# Database settings
# Use Postgres for production
POSTGRES_URL=postgres://username:password@localhost:5432/project_nexus

# Or use SQLite for local development
SQLITE_URL=sqlite:///db.sqlite3

# Redis settings
REDIS_URL=redis://localhost:6379/0

# External API keys (required)
TMDB_API_KEY=your_tmdb_api_key
```

> You must obtain a **TMDB API key** from [The Movie Database](https://developer.themoviedb.org/) to fetch movie data.

---

## 5. Database Setup

Run migrations:

```bash
python manage.py migrate
```

(Optional) Create a superuser:

```bash
python manage.py createsuperuser
```

---

## 6. Run Redis

Make sure Redis is running locally:

```bash
redis-server
```

You can test the connection with:

```bash
redis-cli ping
```

Should return `PONG`.

---

## 7. Load Initial Data

Run this command to sync genres from tmdb:

```bash
python manage.py sync_tmdb_genres
```

---

## 8. Start the Development Server

```bash
python manage.py runserver
```

Visit the API at:

```
http://127.0.0.1:8000/
```

---

## 9. Access API Documentation

* Swagger UI: [http://127.0.0.1:8000/api/v1/docs/](http://127.0.0.1:8000/api/v1/docs/)
* ReDoc: [http://127.0.0.1:8000/api/v1/docs/schema/redoc/](http://127.0.0.1:8000/api/v1/docs/schema/redoc/)

---

## 10. Testing

Run the test suite:

```bash
python manage.py test
```

---

## Troubleshooting

* **Redis not found?** → Ensure it is installed and added to PATH.
* **Database errors?** → Check that PostgreSQL is running or fall back to SQLite.
* **Invalid TMDB key?** → Request a free API key from [TMDB](https://developer.themoviedb.org/).

---

## Next Steps

Once you’ve set up locally, you can:

* Explore endpoints in Swagger UI.
* Import the included Postman collection for quick testing.
* Contribute by opening issues or PRs on [GitHub](https://github.com/<enamyaovi>/project-nexus).
