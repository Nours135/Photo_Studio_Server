#!/bin/bash
set -e

echo "Running DB initialization with env variables:"
echo "  POSTGRES_USER: $POSTGRES_USER"
echo "  APP_USER: $APP_USER"
echo "  APP_DB: $APP_DB"

# create app user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$APP_USER') THEN
            CREATE ROLE $APP_USER LOGIN PASSWORD '$APP_PASSWORD';
        END IF;
    END
    \$\$;
EOSQL

# create app database (must be outside of DO block)
DB_EXISTS=$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_database WHERE datname = '$APP_DB'")
if [ -z "$DB_EXISTS" ]; then
    echo "Creating database $APP_DB..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE $APP_DB OWNER $APP_USER;"
else
    echo "Database $APP_DB already exists, skipping creation."
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$APP_DB" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $APP_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $APP_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $APP_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $APP_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $APP_USER;
EOSQL

# create tables
if [ -f /docker-entrypoint-initdb.d/schema.sql ]; then
    echo "Applying schema.sql as $APP_USER..."
    psql -v ON_ERROR_STOP=1 --username "$APP_USER" --dbname "$APP_DB" -f /docker-entrypoint-initdb.d/schema.sql
else
    echo "⚠️  Warning: schema.sql
