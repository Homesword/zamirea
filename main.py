from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from handler import router
from messages import chat_router 
from profiles import profiles_router
from friends import sub_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path


app = FastAPI()
with open("secret_key.txt", 'r', encoding = 'utf-8') as file:
    secret_key = file.read()  

app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    max_age=172800 # 2 дня 
)

static_path = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# подключаем маршруты 
app.include_router(router)
app.include_router(chat_router)
app.include_router(sub_router)
app.include_router(profiles_router)
