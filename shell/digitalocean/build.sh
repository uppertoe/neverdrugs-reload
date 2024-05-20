#!/bin/sh

# Set up the repository
git clone https://github.com/uppertoe/neverdrugs-reload.git

# Function to prompt for input and create .env file
create_env_file() {
    local file_path=$1
    echo "Please paste your .env content for $file_path. When finished, type 'EOF' on a new line and press Enter."
    
    # Create or clear the .env file
    > "$file_path"

    # Read multiline input
    while IFS= read -r line; do
        if [[ "$line" == "EOF" ]]; then
            break
        fi
        echo "$line" >> "$file_path"
    done

    echo ".env file has been created successfully at $file_path."
}

# Define the target file paths
DJANGO_ENV_FILE=~neverdrugs-reload/.envs/.production/.django
POSTGRES_ENV_FILE=~neverdrugs-reload/.envs/.production/.postgres

# Create .env file for Django
create_env_file "$DJANGO_ENV_FILE"

# Create .env file for Postgres
create_env_file "$POSTGRES_ENV_FILE"

# Build the Docker image
docker compose -f neverdrugs-reload/production.yml build

docker compose -f neverdrugs-reload/production.yml --rm run django python manage.py migrate
docker compose -f neverdrugs-reload/production.yml --rm run django python manage.py collectstatic
