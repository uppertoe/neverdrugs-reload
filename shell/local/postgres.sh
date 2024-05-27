docker exec -it anaesthesia_never_drugs_local_postgres psql -U tcTCsuKcpFyvgWShHBhtHnZxZdDqgRZO -d anaesthesia_never_drugs

-- Check if SSL is enabled
SHOW ssl;

-- Check the SSL certificate and key file paths
SHOW ssl_cert_file;
SHOW ssl_key_file;
SHOW ssl_ca_file;

-- Verify SSL connections
SELECT * FROM pg_stat_ssl;