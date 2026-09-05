#!/bin/sh
set -eu

api_health="$(curl --fail --silent --show-error http://127.0.0.1:8000/health/live)"
analyzer_health="$(curl --fail --silent --show-error http://127.0.0.1:8001/health/live)"

test "$api_health" = '{"status":"live"}'
test "$analyzer_health" = '{"status":"live"}'
printf '%s\n' 'Smoke check passed.'
