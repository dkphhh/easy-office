import os

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

api_url = os.getenv("BACK_END")


config = rx.Config(
    app_name="easy_office",
    api_url=api_url,
    tailwind={
        "theme": {
            "extend": {},
        },
        "plugins": ["@tailwindcss/typography"],
    },
)
