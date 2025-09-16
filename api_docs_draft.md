# Movie Recommendation API Documentation

## Overview

The **ALX Project Nexus Movie Recommendation API** provides movie data, personalized recommendations, and user account features for building interactive movie applications. It integrates with TMDB for movie data, caches responses in Redis for performance, and delivers results in a consistent, serialized JSON format. The API is designed for frontend developers, mobile developers, and backend systems that need access to user-specific movie data and recommendations.

---

## User Flow

Here’s how a typical user will interact with the app:

1. **Register / Login**

   * User creates an account or logs in to get an authentication token.

2. **Browse Movies**

   * User sees a paginated list of trending movies (from TMDB, cached in Redis).
   * User can filter movies by genre or rating.

3. **View Movie Details**

   * User clicks on a movie to see detailed info.

4. **Favorite Movies**

   * User can add/remove movies from their favorites catalogue.
   * User can view their own favorite list anytime.

5. **Personalized Recommendations**

   * Based on user’s favorite genres (from their profile), they see recommended movies.

---

## Authentication

* Authentication is handled with **JWT tokens**.
* Include the token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

* Some endpoints are public (`AllowAny`), while others require authentication.
* Tokens may expire; refresh endpoints should be used if implemented.

---

## Error Handling

The API uses standard HTTP status codes to indicate success or failure:

* `200 OK` – Request successful
* `201 Created` – Resource created successfully
* `204 No Content` – Resource deleted successfully
* `400 Bad Request` – Invalid request payload or parameters
* `401 Unauthorized` – Missing or invalid authentication token
* `403 Forbidden` – Insufficient permissions
* `404 Not Found` – Resource does not exist
* `500 Internal Server Error` – Unexpected server error

---

## Data Models

### User

```json
{
  "id": 1,
  "email": "user@example.com",
  "date_joined": "2025-09-16",
  "favorite_genres": [28, 18]
}
```

### Movie

```json
{
  "id": 123,
  "title": "Inception",
  "description": "A dream within a dream...",
  "release_date": "2010-07-16",
  "poster_url": "https://image.tmdb.org/t/p/w500/qwe123.jpg",
  "popularity": 98.7,
  "genres": [28, 878]
}
```

### Favorite

```json
{
  "id": 123,
  "title": "Inception",
  "poster_url": "https://image.tmdb.org/t/p/w500/qwe123.jpg",
  "date_favorited": "2025-09-16T10:00:00Z"
}
```

---

## Accounts Endpoints

### Register a New User

```http
POST /api/v1/accounts/register/
```

**Request body**

```json
{
  "email": "user@example.com",
  "password": "strongpassword123"
}
```

**Response**

```json
{
  "id": 1,
  "email": "user@example.com",
  "token": "<jwt_token>"
}
```

Example with `curl`:

```bash
curl -X POST https://api.example.com/api/v1/accounts/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com", "password":"strongpassword123"}'
```

---

### Login

```http
POST /api/v1/accounts/login/
```

**Request body**

```json
{
  "email": "user@example.com",
  "password": "strongpassword123"
}
```

**Response**

```json
{
  "token": "<jwt_token>"
}
```

---

### Get User Profile

```http
GET /api/v1/accounts/<user_id>/
```

**Response**

```json
{
  "id": 1,
  "email": "user@example.com",
  "date_joined": "2025-09-16",
  "favorite_genres": [28, 18]
}
```

---

## Movies Endpoints

### List Trending Movies (Public)

```http
GET /api/v1/movies/trending/
```

**Response**

```json
{
  "count": 100,
  "next": "/api/v1/movies/trending/?page=2",
  "previous": null,
  "results": [
    {
      "id": 123,
      "title": "Inception",
      "description": "A dream within a dream...",
      "release_date": "2010-07-16",
      "poster_url": "https://image.tmdb.org/t/p/w500/qwe123.jpg",
      "popularity": 98.7,
      "genres": [28, 878]
    }
  ]
}
```

---

### Movie Detail (Public)

```http
GET /api/v1/movies/<movie_id>/
```

**Response**

```json
{
  "id": 123,
  "title": "Inception",
  "description": "A dream within a dream...",
  "release_date": "2010-07-16",
  "poster_url": "https://image.tmdb.org/t/p/w500/qwe123.jpg",
  "popularity": 98.7,
  "genres": [28, 878]
}
```

---

### User Favorites (Auth Required)

**List Favorites**

```http
GET /api/v1/movies/favorites/
```

**Response**

```json
[
  {
    "id": 123,
    "title": "Inception",
    "poster_url": "https://image.tmdb.org/t/p/w500/qwe123.jpg",
    "date_favorited": "2025-09-16T10:00:00Z"
  }
]
```

**Add Favorite**

```http
POST /api/v1/movies/<movie_id>/favorite/
```

Response: `201 Created`

**Remove Favorite**

```http
DELETE /api/v1/movies/<movie_id>/favorite/
```

Response: `204 No Content`

---

### Recommended Movies (Auth Required)

```http
GET /api/v1/movies/recommended/
```

**Response**

```json
[
  {
    "id": 321,
    "title": "The Matrix",
    "poster_url": "https://image.tmdb.org/t/p/w500/abc123.jpg",
    "genres": [28, 878]
  }
]
```

---

## Notes for Frontend

* **Unauthenticated users** → can browse trending & detail views.
* **Authenticated users** → can manage favorites and see recommendations.
* All responses are **JSON**.
* Authentication must be included in the request headers.
* CORS is enabled for web clients.
* Content-Type for requests must be `application/json`.

---

## Versioning

* Current version: **v1** (`/api/v1/`)
* Future changes will be introduced under new version paths (e.g., `/api/v2/`).

---

# AVAILABLE ENDPOINTS

## Accounts

| HTTP Method | Path                          | Functionality                           | Permissions   | Extra Notes                 |
| ----------- | ----------------------------- | --------------------------------------- | ------------- | --------------------------- |
| POST        | /api/v1/accounts/register/    | Create a new user account               | AllowAny      | Returns token and user data |
| POST        | /api/v1/accounts/login/       | Authenticate user with email & password | AllowAny      | Returns JWT token           |
| GET         | /api/v1/accounts/\<user\_id>/ | Retrieve user profile                   | Authenticated | Includes favorite genres    |

## Movies

| HTTP Method | Path                                  | Functionality                    | Permissions   | Extra Notes                           |
| ----------- | ------------------------------------- | -------------------------------- | ------------- | ------------------------------------- |
| GET         | /api/v1/movies/trending/              | List trending movies             | AllowAny      | Paginated, can filter by genre/rating |
| GET         | /api/v1/movies/\<movie\_id>/          | Get movie detail                 | AllowAny      | Cached if available                   |
| GET         | /api/v1/movies/favorites/             | List user’s favorite movies      | Authenticated | Shows date\_favorited                 |
| POST        | /api/v1/movies/\<movie\_id>/favorite/ | Add movie to favorites           | Authenticated | Saves to DB and returns 201           |
| DELETE      | /api/v1/movies/\<movie\_id>/favorite/ | Remove movie from favorites      | Authenticated | Returns 204                           |
| GET         | /api/v1/movies/recommended/           | Get personalized recommendations | Authenticated | Based on profile genres               |

---
