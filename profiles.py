import sqlite3 as sq
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os 
from fastapi.responses import RedirectResponse
from get_methods import * 

profiles_router = APIRouter()
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)
db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db") 

@profiles_router.get("/{id}")
async def get_profile(request: Request, id: int):
    #### вошёл ли юзер
    if not(request.session.get("user_logged")):
        return RedirectResponse(url="/")

    #### если такого пользователя не существует
    flag = True
    if not(id < 1):
        with sq.connect(db_path) as con:
            cur = con.cursor() 
            cur.execute("SELECT MAX(ROWID) FROM users")
            if not(id > int(cur.fetchone()[0])):
                flag = False
    if flag: return RedirectResponse(url="/")

    user_data = request.session['user_data']
    int_rowid = int(user_data['rowid'])

    # если юзер просматривает свой профиль
    if id == int_rowid: 
        name_profile = user_data['name']
        login_profile = user_data['login']
        path_profile = user_data['path']
        rowid_profile = user_data['rowid']
    else:
         with sq.connect(db_path) as con:
            cur = con.cursor() 
            cur.execute(f"SELECT * FROM users WHERE ROWID = ? LIMIT 1", (id,)) 
            data_now_profile = cur.fetchone()
            name_profile = data_now_profile[0]
            login_profile = data_now_profile[1]
            path_profile = data_now_profile[3]
            rowid_profile = id
            
    #### правый блок
    other_chats = get_other_chats(int_rowid)
    other_subscribers = get_subscribers(int_rowid)

    #### медийные данные
    with sq.connect(db_path) as con:
            cur = con.cursor() 
            cur.execute("SELECT * FROM media WHERE ROWID = (?) LIMIT 1", (id,))
            media_data = cur.fetchone()
            posts, likes = media_data[0], media_data[1]
            sub, followers = media_data[2], media_data[3]

    
    return templates.TemplateResponse("profiles.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                     "path": user_data['path'], "rowid": user_data['rowid'],
                                                     "name_profile": name_profile, "login_profile": login_profile,
                                                     "path_profile": path_profile, "rowid_profile": rowid_profile,
                                                     "other_chats": other_chats, "other_subscribers": other_subscribers,
                                                     "posts": posts, "likes": likes, "sub": sub, "followers": followers})
