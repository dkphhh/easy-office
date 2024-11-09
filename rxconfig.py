import os
import urllib.parse

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

api_url = os.getenv("BACK_END")
db_username = os.getenv("DB_USERNAME")
db_password: str = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")


def get_db_connection():
    username = db_username
    password = urllib.parse.quote_plus(db_password)
    host = db_host
    port = db_port
    database = "postgres"

    connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    return connection_string


config = rx.Config(
    app_name="easy_office",
    loglevel="info",
    api_url=api_url,
    db_url=get_db_connection(),
    tailwind={
        "theme": {
            "extend": {},
        },
        "plugins": ["@tailwindcss/typography"],
    },
)
