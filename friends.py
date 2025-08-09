from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import RedirectResponse
import os
import sqlite3 as sq
from get_methods import *


sub_router = APIRouter(prefix="/subscriptions")
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)
db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db")


# подписки
@sub_router.get("/")
async def test_friends(request: Request):
    user_logged = request.session.get("user_logged")
    if not(user_logged):
        return RedirectResponse(url="/login")
    user_data = request.session['user_data']
    
    #### правый блок
    int_rowid = int(user_data['rowid'])
    other_chats = get_other_chats(int_rowid)
    other_subscribers = get_subscribers(int_rowid)

    with sq.connect(db_path) as con:
        cur = con.cursor()
        #### счётчик подписчиков и подписок
        cur.execute("SELECT sub, followers FROM media WHERE ROWID = ?", (int_rowid,))
        score_sub, score_followers = cur.fetchone()

        #### подписки
        cur.execute("""
            SELECT 
                u.name, u.login, u.avatar,
                m.sub, m.followers,
                s.author
            FROM subscribers s
            JOIN users u ON u.ROWID = s.author
            JOIN media m ON m.ROWID = s.author
            WHERE s.subscriber = ?
        """, (int_rowid,))
        sub_block = cur.fetchall()

        #### подписчики
        cur.execute("""
        SELECT u.name, u.login, u.avatar, m.sub, m.followers, u.ROWID
        FROM subscribers s
        JOIN users u ON u.ROWID = s.subscriber
        JOIN media m ON m.ROWID = s.subscriber
        WHERE s.author = ?
        """, (int_rowid,))

        followers_block = cur.fetchall()

    return templates.TemplateResponse("friends.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                     "path": user_data['path'], "rowid": user_data['rowid'],
                                                     "other_chats": other_chats, "other_subscribers": other_subscribers,
                                                     "score_sub": score_sub, "score_followers": score_followers,
                                                     "sub_block": sub_block, "followers_block": followers_block})