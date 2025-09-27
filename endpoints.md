# AVAILABLE ENDPOINTS

This document provides an overview of all available API endpoints, their methods, permissions, and descriptions.  
For detailed examples, see the Postman documentation or the hosted Swagger UI.

---

## Users

| HTTP Method | Path                                   | Functionality                                | Permissions     | Extra Notes                                      |
| ----------- | -------------------------------------- | -------------------------------------------- | --------------- | ------------------------------------------------ |
| GET         | /api/v1/users/                         | List all users                               | Authenticated   | Admin/staff only in production                   |
| POST        | /api/v1/users/                         | Register a new user                          | AllowAny        | Returns created user data                        |
| GET         | /api/v1/users/{user_id}/               | Retrieve user details                        | Authenticated   | User can only view their own profile             |
| PUT         | /api/v1/users/{user_id}/               | Fully update a user                          | Authenticated   | Can only update their own account                |
| PATCH       | /api/v1/users/{user_id}/               | Partially update a user                      | Authenticated   | e.g. `first_name`, `last_name`, `email`          |
| DELETE      | /api/v1/users/{user_id}/               | Delete a user account                        | Authenticated   | User can delete their own account                |
| GET         | /api/v1/users/edit_profile/            | Get the authenticated user’s profile         | IsUser          | Profile endpoint scoped to the current user      |
| PUT         | /api/v1/users/edit_profile/            | Update the authenticated user’s profile      | IsUser          | Replace all profile fields                       |
| PATCH       | /api/v1/users/edit_profile/            | Partially update user profile                | IsUser          | Update description, genres, or avatar            |
| POST        | /api/v1/users/password_change/         | Change password for authenticated user       | Authenticated   | Email service integration WIP                    |
| POST        | /api/v1/users/password_reset/          | Reset password                               | AllowAny        | Email service integration WIP                    |
| GET         | /api/v1/users/recommended_movies/      | Get recommended movies                       | Authenticated   | Based on genres; falls back to trending          |
| GET         | /api/v1/users/view_catalogue/          | View list of user’s favorited movies         | Authenticated   | Highlight endpoint                               |

---

## Movies

| HTTP Method | Path                                   | Functionality                                | Permissions     | Extra Notes                                      |
| ----------- | -------------------------------------- | -------------------------------------------- | --------------- | ------------------------------------------------ |
| GET         | /api/v1/movies/                        | List trending movies                         | AllowAny        | Paginated (60 results, 5 per page); cached       |
| GET         | /api/v1/movies/{movie_id}/             | Get details of a specific movie              | AllowAny        | Public, cached                                   |
| GET         | /api/v1/movies/search/?q={query}       | Search movies by title                       | AllowAny        | Requires query parameter `q`                     |
| POST        | /api/v1/movies/{movie_id}/favorite_movie/ | Add movie to user’s favorites              | Authenticated   | Saves to DB and returns 201                      |
| DELETE      | /api/v1/movies/{movie_id}/remove_favorite/ | Remove a movie from favorites              | Authenticated   | Returns `204 No Content`                         |

---

## Genres

| HTTP Method | Path                                   | Functionality                                | Permissions     | Extra Notes                                      |
| ----------- | -------------------------------------- | -------------------------------------------- | --------------- | ------------------------------------------------ |
| GET         | /api/v1/genres/                        | List all available genres                    | AllowAny        | For use in search filters and recommendations    |

---

## Authentication

| HTTP Method | Path                                   | Functionality                                | Permissions     | Extra Notes                                      |
| ----------- | -------------------------------------- | -------------------------------------------- | --------------- | ------------------------------------------------ |
| POST        | /api/v1/token/                         | Obtain JWT access and refresh tokens         | AllowAny        | Requires email & password                        |
| POST        | /api/v1/token/refresh/                 | Refresh an expired access token              | AllowAny        | Requires valid refresh token                     |
| GET         | /api/v1/token/retrieve_api_key/        | Retrieve API key                             | Authenticated   | Developer feature (optional)                     |

---

## Notes

- All protected endpoints require `Authorization: Bearer <token>` in the request header.  
- Errors follow standard HTTP status codes (`401 Unauthorized`, `403 Forbidden`, etc.).  
- For interactive exploration, visit the [Swagger UI](https://alx-project-nexus-movie-api.onrender.com/docs).  
