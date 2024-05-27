import psycopg
import os

def test_connection():
    connection_params = {
        "dbname": os.getenv('POSTGRES_DB'),
        "user": os.getenv('POSTGRES_USER'),
        "password": os.getenv('POSTGRES_PASSWORD'),
        "host": os.getenv('POSTGRES_HOST'),
        "port": os.getenv('POSTGRES_PORT'),
        "sslmode": 'require',
        "sslrootcert": os.getenv('DB_SSLROOTCERT'),
        "sslcert": os.getenv('DB_SSLCERT'),
        "sslkey": os.getenv('DB_SSLKEY'),
    }

    try:
        conn = psycopg.connect(**connection_params)
        print("Connection successful")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()