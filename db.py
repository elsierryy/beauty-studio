import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg.connect(
        host="localhost",
        port=5432,
        dbname="beauty_studio",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),
    )
