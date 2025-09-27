# Project Nexus – Movie Recommendation API

## Overview

The API provides trending and recommended movie data, user account management, and personalized recommendations. It integrates with TMDB for movie data, caches responses in Redis for performance, and delivers consistent JSON responses for frontend, mobile, and backend developers.

* Live Swagger Docs: [Swagger-UI](https://alx-project-nexus-movie-api.onrender.com/api/v1/docs/). 
* You can also access the postman collections in this repo under [postman](/project_nexus/postman.json) and access the postman documentation with full examples at [Postman Documentation](https://documenter.getpostman.com/view/40330540/2sB3QDvXzp).

## API Features

* API endpoints for trending and recommended movies
* Search movies by title
* User authentication using JWT
* Save and manage favorites and watchlists
* Redis caching for performance optimization

## Public vs. Protected Endpoints


* **Public Endpoints**: Browse trending movies, search movies, view genres
* **Protected Endpoints**: Manage favorites, edit user profile, access personalized recommendations

The list of all the endpoints can be found in this repo at [endpoints.md](/endpoints.md)

## Example Request

```
GET https://alx-project-nexus-movie-api.onrender.com/api/v1/movies/
```

## Authentication

* Authentication is JWT-based (access and refresh tokens via `/token/` and `/token/refresh/`)
* Example header:

```
Authorization: Bearer <token>
```

## Rate Limits

* Authenticated users: 1000 requests/day
* Anonymous users: 500 requests/day
* `HTTP 429` returned if the limit is exceeded

## Error Handling

The API makes use of standard HTTP status codes to indicate the state of a response. Below are the codes used and what they mean.

* 200 OK – Request successful
* 201 Created – Resource created successfully
* 204 No Content – Resource deleted successfully
* 400 Bad Request – Invalid payload or parameters
* 401 Unauthorized – Missing or invalid authentication token
* 403 Forbidden – Insufficient permissions
* 404 Not Found – Resource does not exist
* 500 Internal Server Error – Unexpected server error
* 502 Bad Gateway – External API failure

## Disclaimer

The examples in this documentation have been modified for security reasons. Sensitive values such as JWT tokens, user IDs, and private request/response data have been removed or altered. The sample requests and responses are illustrative only and may not reflect the exact live data. For interactive testing, please visit the Swagger UI hosted with the API.

---

For local development and setup instructions, see [SETUP.md](SETUP.md).