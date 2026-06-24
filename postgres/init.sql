-- Initialisation script — runs once on first container boot.
-- Creates the two application schemas owned by the app user.

CREATE SCHEMA IF NOT EXISTS calendar_app AUTHORIZATION app;
CREATE SCHEMA IF NOT EXISTS laravel      AUTHORIZATION app;

-- Set the default search_path so the app user finds calendar_app first.
ALTER ROLE app SET search_path TO calendar_app, public;
