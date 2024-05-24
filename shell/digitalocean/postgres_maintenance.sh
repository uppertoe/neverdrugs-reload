#!/bin/sh
docker exec -it neverdrugs-reload-postgres-1 psql -U tcTCsuKcpFyvgWShHBhtHnZxZdDqgRZO -d anaesthesia_never_drugs -c "VACUUM ANALYZE;"
