FROM postgres:16

COPY init-scripts/postgres-init.sql /docker-entrypoint-initdb.d/01-postgres-init.sql
RUN chmod 644 /docker-entrypoint-initdb.d/01-postgres-init.sql
