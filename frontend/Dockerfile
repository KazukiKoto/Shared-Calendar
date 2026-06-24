FROM php:8.3-cli-alpine AS base

RUN apk add --no-cache \
    curl \
    libpq-dev \
    zip \
    unzip \
    git \
    && docker-php-ext-install pdo_pgsql

# Populate $_ENV so phpdotenv can read OS environment variables (e.g. APP_KEY)
# The alpine image uses PHP's production defaults which omit 'E' from variables_order.
RUN printf 'variables_order = EGPCS\n' > /usr/local/etc/php/conf.d/99-vars.ini

# Install Composer from its official image
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www

# ── Development ──────────────────────────────────────────────────────────────
FROM base AS development

# Install dependencies first for layer caching (cached unless composer.json changes)
COPY composer.json ./
RUN composer install --no-scripts --no-autoloader --no-interaction --prefer-dist

# Copy the full application source on top
COPY . .

# Generate the optimised autoloader and discover Laravel packages
RUN composer dump-autoload --optimize && \
    APP_KEY="base64:c2hhcmVkLWNhbGVuZGFyLWRldi1rZXktMTIzNDU2Nzg=" \
    php artisan package:discover --ansi

# Ensure storage and cache directories exist and are writable
RUN mkdir -p storage/framework/{sessions,views,cache/data} bootstrap/cache \
    && chmod -R 777 storage bootstrap/cache

# Entrypoint handles missing vendor/ (bind-mount first-run) and missing .env
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 9000
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=9000"]
