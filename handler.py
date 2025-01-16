from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import RedirectResponse
import secrets
import os
import sqlite3 as sq
import bcrypt


router = APIRouter()
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)


@router.get("/") 
async def index(request: Request):
    user_logged = request.session.get("user_logged")
    if not(user_logged):
        return RedirectResponse(url="/login")
    user_data = request.session['user_data']
    return templates.TemplateResponse("index.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                     "path": user_data['path'], "rowid": user_data['rowid']})


@router.get('/login')
async def login_page(request: Request):
    user_logged = request.session.get("user_logged")
    if user_logged:
        return RedirectResponse(url="/")
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token, "text_header": "Войти"})


@router.post('/login') 
async def login(request: Request):
    form_data = await request.form() 

    # проверка csrf
    csrf_token = form_data.get("csrf_token")  
    if request.session["csrf_token"] != csrf_token:
        return RedirectResponse(url="/login", status_code=303)
    
    login = form_data.get("login")
    password = form_data.get("password")  
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    with sq.connect(db_path) as con:
        cur = con.cursor() 
        cur.execute(f"SELECT * FROM users WHERE login = ? LIMIT 1", (login.lower(),)) 
        test_user = cur.fetchone()
        if (test_user) and (check_password(test_user[2], password)): # успешный вход
            request.session["user_logged"] = True
            request.session["user_data"] = {
                'name': test_user[0],
                'login': login.lower(),
                'path': test_user[3],
                'rowid': f"{cur.lastrowid}"
            }
            return RedirectResponse(url="/", status_code=303)
        else: # неправильная почта или пароль
            return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token, "text_header": "Неправильная почта или пароль."})
 

@router.get('/register')
async def register_page(request: Request):
    user_logged = request.session.get("user_logged")
    if user_logged:
        return RedirectResponse(url="/")
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("register.html", {"request": request, "csrf_token": csrf_token, "text_header": "Регистрация"})


@router.post('/register')
async def register(request: Request):
    form_data = await request.form()  
    csrf_token = form_data.get("csrf_token")  

    if request.session["csrf_token"] != csrf_token: # проверка csrf
        return RedirectResponse(url="/register", status_code=303)
    
    pass1 = form_data.get("pass1")
    pass2 = form_data.get("pass2")

    if pass1 != pass2: # разные пароли
        return templates.TemplateResponse("register.html", {"request": request, "csrf_token": csrf_token, "text_header": "Пароли не совпадают."})
    
    login = form_data.get("login")
    name = form_data.get("name")
    db_path = os.path.join(os.path.dirname(__file__), "users.db")

    with sq.connect(db_path) as con: # проверка, если логин уже есть в БД
        cur = con.cursor() 
        cur.execute(f"SELECT login FROM users WHERE login = ? LIMIT 1", (login,))
        test_login = cur.fetchone()
        if test_login: 
            return templates.TemplateResponse("register.html", {"request": request, "csrf_token": csrf_token, "text_header": "Аккаунт с данной почтой уже зарегистрирован."})
    
    # запись нового пользователя в БД
    hashed_password = hash_password(pass1) 
    cur.execute(f"INSERT INTO users (name, login, password) VALUES (?, ?, ?)", (name, login.lower(), hashed_password))
    con.commit()
    request.session["user_logged"] = True
    request.session["user_data"] = {
        'name': name,
        'login': login.lower(),
        'path': "/static/assets/images/my-profile.jpg",
        'rowid': f"{cur.lastrowid}"
    }
    return RedirectResponse(url="/", status_code=303)  


@router.get('/privacy')
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303) 


def generate_csrf_token():
    return secrets.token_urlsafe(32)


def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def check_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
