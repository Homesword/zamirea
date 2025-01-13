from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from handler import router
from fastapi.staticfiles import StaticFiles
from pathlib import Path


app = FastAPI()
with open("secret_key.txt", 'r', encoding = 'utf-8') as file:
    secret_key = file.read()  

app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key
)

static_path = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# подключаем маршруты из handler.py
app.include_router(router)
