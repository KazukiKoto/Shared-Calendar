#!/bin/sh
set -e

if [ ! -f vendor/autoload.php ]; then
    echo "→ vendor/ not found — running composer install..."
    composer install --no-interaction --prefer-dist --optimize-autoloader
fi

# phpdotenv (Laravel's env loader) does not reliably read $_ENV in PHP's
# built-in web server mode. Bridge Docker env vars into .env explicitly.
# Values are double-quoted so phpdotenv accepts entries with spaces.
printenv | sed 's/^\([^=]*\)=\(.*\)$/\1="\2"/' > .env

exec "$@"
