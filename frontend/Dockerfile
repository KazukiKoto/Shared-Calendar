FROM php:8.3-cli-alpine AS base

RUN apk add --no-cache \
    curl \
    libpq-dev \
    zip \
    unzip \
    git \
    && docker-php-ext-install pdo_pgsql

# Populate $_ENV so phpdotenv can read OS environment variables (e.g. APP_KEY).
# Alpine's PHP defaults omit 'E' from variables_order.
RUN printf 'variables_order = EGPCS\n' > /usr/local/etc/php/conf.d/99-vars.ini

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www

# ── Development ──────────────────────────────────────────────────────────────
FROM base AS development

COPY composer.json ./
RUN composer install --no-scripts --no-autoloader --no-interaction --prefer-dist

COPY . .

RUN composer dump-autoload --optimize && \
    APP_KEY="base64:c2hhcmVkLWNhbGVuZGFyLWRldi1rZXktMTIzNDU2Nzg=" \
    php artisan package:discover --ansi

RUN mkdir -p storage/framework/{sessions,views,cache/data} bootstrap/cache \
    && chmod -R 777 storage bootstrap/cache

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 9000
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=9000"]

# ── Production ───────────────────────────────────────────────────────────────
FROM base AS production

# composer.lock* copies the lock file if present (recommended for reproducible
# production builds); falls back to resolving from composer.json if absent.
COPY composer.json composer.lock* ./
RUN composer install \
    --no-dev \
    --no-scripts \
    --no-autoloader \
    --no-interaction \
    --prefer-dist

COPY . .

RUN composer dump-autoload --optimize --classmap-authoritative --no-dev && \
    APP_KEY="base64:c2hhcmVkLWNhbGVuZGFyLWRldi1rZXktMTIzNDU2Nzg=" \
    php artisan package:discover --ansi

RUN mkdir -p storage/framework/{sessions,views,cache/data} bootstrap/cache \
    && chmod -R 775 storage bootstrap/cache

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

RUN adduser -D -H -s /bin/sh appuser \
    && chown -R appuser:appuser storage bootstrap/cache

USER appuser

EXPOSE 9000
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=9000"]
