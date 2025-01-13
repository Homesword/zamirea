from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import RedirectResponse
import secrets


router = APIRouter()
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)


@router.get("/") # .get тут - тип запроса
async def index(request: Request):
    user_logged = request.session.get("user_logged")
    if not(user_logged):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("index.html", {"request": request})


@router.get('/login')
async def login_page(request: Request):
    user_logged = request.session.get("user_logged")
    if user_logged:
        return RedirectResponse(url="/")
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})


@router.post('/login') # логика входа в аккаунт через БД
async def login(request: Request):
    form_data = await request.form()  
    # проверка csrf
    csrf_token = form_data.get("csrf_token")  
    if request.session["csrf_token"] != csrf_token:
        return RedirectResponse(url="/login")
    login = form_data.get("login")
    password = form_data.get("password")  
    pass 


@router.get('/register')
async def register_page(request: Request):
    user_logged = request.session.get("user_logged")
    if user_logged:
        return RedirectResponse(url="/")
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("register.html", {"request": request, "csrf_token": csrf_token})


@router.post('/register')
async def register(request: Request): # логика регистрации через БД
    form_data = await request.form()  
    # проверка csrf
    csrf_token = form_data.get("csrf_token")  
    if request.session["csrf_token"] != csrf_token:
        return RedirectResponse(url="/register")
    name = form_data.get("name")
    login = form_data.get("login")
    pass1 = form_data.get("pass1")
    pass2 = form_data.get("pass2")
    pass


@router.get('/privacy')
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


# генерация токена для каждой формы
def generate_csrf_token():
    return secrets.token_urlsafe(32)
