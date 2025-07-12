import sqlite3 as sq
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os 
from fastapi.responses import RedirectResponse



profiles_router = APIRouter()
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)
db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db") 

@profiles_router.get("/{id}")
async def get_profile(request: Request, id: int):
    # вошёл ли юзер
    if not(request.session.get("user_logged")):
        return RedirectResponse(url="/")
    
    user_data = request.session['user_data']

    # если юзер просматривает свой профиль
    if id == int(user_data['rowid']): 
        name_profile = user_data['name']
        login_profile = user_data['login']
        path_profile = user_data['path']
        rowid_profile = user_data['rowid']
    else:
         with sq.connect(db_path) as con:
            cur = con.cursor() 
            # возьми 1 элемент таблицы, где номер ячейки равен rowid
            cur.execute(f"SELECT * FROM users WHERE ROWID = ? LIMIT 1", (id,)) 
            data_now_profile = cur.fetchone()
            name_profile = data_now_profile[0]
            login_profile = data_now_profile[1]
            path_profile = data_now_profile[3]
            rowid_profile = id
            

    return templates.TemplateResponse("profiles.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                     "path": user_data['path'], "rowid": user_data['rowid'],
                                                     "name_profile": name_profile, "login_profile": login_profile,
                                                     "path_profile": path_profile, "rowid_profile": rowid_profile})


