#!/bin/sh
set -eu

# Install Temporal's native persistence and visibility schemas before the server starts.
for schema in temporal visibility; do
  database=temporal
  if [ "$schema" = visibility ]; then database=temporal_visibility; fi
  temporal-sql-tool --plugin postgres12 --ep postgres -u "$POSTGRES_USER" -p 5432 \
    --db "$database" setup-schema -v 0.0
  temporal-sql-tool --plugin postgres12 --ep postgres -u "$POSTGRES_USER" -p 5432 \
    --db "$database" update-schema -d "/etc/temporal/schema/postgresql/v12/$schema/versioned"
done
