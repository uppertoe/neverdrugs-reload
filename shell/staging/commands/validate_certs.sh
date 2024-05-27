# Validate Server Certificate
sudo openssl x509 -in /home/uppertoe/ssl/postgresql/server/server.crt -text -noout

# Validate Server Key
sudo openssl rsa -in /home/uppertoe/ssl/postgresql/server/server.key -check

# Validate Client Certificate
sudo openssl x509 -in /home/uppertoe/ssl/postgresql/client/client.crt -text -noout

# Validate Client Key
sudo openssl rsa -in /home/uppertoe/ssl/postgresql/client/client.key -check

# Verify CA Certificate
sudo openssl x509 -in /home/uppertoe/ssl/postgresql/ca/ca.crt -text -noout
