#!/bin/bash

# Load environment variables (expects TMDB_API_KEY in .env)
source .env

write_file="data.json"
error_log="errors.txt"

tmp_body=$(mktemp)
tmp_error=$(mktemp)

trap 'rm -f "$tmp_body" "$tmp_error"' EXIT

# Perform the request, capture both body and HTTP status
http_status=$(curl -s -o "$tmp_body" -w "%{http_code}" \
    --request GET \
    --url 'https://api.themoviedb.org/3/discover/movie?include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc' \
    --header "Authorization: Bearer $TMDB_API_KEY" \
    --header "accept: application/json" \
    2>"$tmp_error")

exit_code=$?

if [ "$exit_code" -ne 0 ]; then
    {
    echo "[$(date)] Curl failed with exit code: $exit_code"
    cat "$tmp_error"
    } >> "$error_log"
    exit "$exit_code"
fi

if [ "$http_status" -eq 200 ]; then
    mv "$tmp_body" "$write_file"
    echo "Response written to file: $write_file"
else
    {
    echo "[$(date)] Request failed. HTTP Status: $http_status"
    cat "$tmp_body"
    } >> "$error_log"
    rm -f "$tmp_body"
fi
