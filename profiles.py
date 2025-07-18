import sqlite3 as sq
from fastapi import APIRouter, Request, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os 
from fastapi.responses import RedirectResponse
from get_methods import * 
from datetime import datetime

profiles_router = APIRouter()
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)
db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db") 

@profiles_router.get("/{id}")
async def get_profile(request: Request, id: int):
    #### вошёл ли пользователь
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
            posts, sub = media_data[0], media_data[1]
            likes, followers = media_data[2], media_data[3]
            #### посты и понравившиеся
            cur.execute("SELECT * FROM posts WHERE who = (?)", (id,))
            user_posts = cur.fetchall()
            cur.execute("SELECT * FROM favorites WHERE who = (?)", (id,))
            user_likes = cur.fetchall()

    #### подписки
    with sq.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT 
                u.name, u.login, u.avatar,
                m.sub, m.followers,
                s.author
            FROM subscribers s
            JOIN users u ON u.ROWID = s.author
            JOIN media m ON m.ROWID = s.author
            WHERE s.subscriber = ?
        """, (id,))
        sub_block = cur.fetchall()
    print(sub_block)







    return templates.TemplateResponse("profiles.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                     "path": user_data['path'], "rowid": user_data['rowid'],
                                                     "name_profile": name_profile, "login_profile": login_profile,
                                                     "path_profile": path_profile, "rowid_profile": rowid_profile,
                                                     "other_chats": other_chats, "other_subscribers": other_subscribers,
                                                     "posts": posts, "likes": likes, "sub": sub, "followers": followers,
                                                     "user_posts": user_posts, "user_likes": user_likes, "sub_block": sub_block})

# проверка расширения
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# выгрузка аватара
@profiles_router.post("/upload_avatar")
async def upload_avatar(request: Request, avatar: UploadFile = File(...)):
    user_data = request.session['user_data']

    if not user_data:
        return RedirectResponse(url="/", status_code=303)
    
    rowid = str(user_data['rowid'])
    

    #### ничего не отправил
    if avatar.filename == '':
        return RedirectResponse(url=f"/{rowid}", status_code=303)

    #### проверка на расширение
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
    if allowed_file(avatar.filename):
        contents = await avatar.read()

        #### если больше допустимого размера
        if len(contents) > MAX_FILE_SIZE:
            return RedirectResponse(url=f"/{rowid}", status_code=303)

        #### успешно, сохраняем аватарку
        filename = f"{rowid}{(os.path.splitext(avatar.filename)[1])}"
        path = f"{os.path.dirname(os.getcwd())}/static/assets/images/avatars"
        save_path = os.path.join(path, filename)
        with open(save_path, "wb") as f:
            f.write(contents)

        #### меняем аватар в сети        
        new_avatar_path = os.path.join('/static/assets/images/avatars', filename)
        user_data['path'] = new_avatar_path
        with sq.connect(db_path) as con:
            cur = con.cursor() 
            cur.execute("UPDATE users SET avatar = (?) WHERE ROWID = (?)", (new_avatar_path, user_data['rowid']))

        print(f"Пользователь {user_data['login']} успешно сменил аватарку")
        return RedirectResponse(url=f"/{rowid}", status_code=303)
    else:
        return RedirectResponse(url=f"/{rowid}", status_code=303)
    
# создание нового поста
@profiles_router.post("/new-post")
async def upload_avatar(request: Request, text_post: str = Form(...)): 
    with sq.connect(db_path) as con:
            cur = con.cursor() 
            rowid = request.session['user_data']['rowid']
            date = datetime.now()
            cur.execute("INSERT INTO posts (who, timestamp, text, likes) VALUES (?, ?, ?, ?)", (rowid, date.strftime("%Y.%m.%d %H:%M:%S"), text_post, 0))
            cur.execute("UPDATE media SET posts = posts + 1 WHERE ROWID = ?", (rowid,))
            con.commit()
    return RedirectResponse(url=f"/{rowid}", status_code=303)

# редактирование поста
@profiles_router.post("/edit-post")
async def edit_post(request: Request,  post_id: int = Form(...), edited_text: str = Form(...)):
    rowid = request.session['user_data']['rowid']
    with sq.connect(db_path) as con:
            cur = con.cursor() 
            # получаем ROWID поста, который нужно отредактировать
            cur.execute("SELECT ROWID FROM posts WHERE who = (?) ORDER BY ROWID DESC LIMIT 1 OFFSET (?)",
        (rowid, post_id-1))
            rowid_post = cur.fetchone()[0]    
            date = datetime.now()
            # редактируем пост
            cur.execute("UPDATE posts SET timestamp = ?, text = ? WHERE ROWID = ?",
                (date.strftime("%Y.%m.%d %H:%M:%S"), edited_text, rowid_post))
            con.commit()

    return RedirectResponse(url=f"/{rowid}", status_code=303) 

@profiles_router.post("/delete-post")
async def delete_post(request: Request, post_id: int = Form(...)): 
     rowid = request.session['user_data']['rowid']
     with sq.connect(db_path) as con:
            cur = con.cursor() 
            # получаем ROWID поста, который нужно удалить
            cur.execute("SELECT ROWID FROM posts WHERE who = (?) ORDER BY ROWID DESC LIMIT 1 OFFSET (?)",
        (rowid, post_id-1))
            rowid_post = cur.fetchone()[0]   
            # удаляем пост
            cur.execute("DELETE FROM posts WHERE ROWID = ?", (rowid_post,))
            cur.execute("UPDATE media SET posts = posts - 1 WHERE ROWID = ?", (rowid,))
            con.commit()
     return RedirectResponse(url=f"/{rowid}", status_code=303) 

    