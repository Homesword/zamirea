import sqlite3 as sq
from fastapi import APIRouter, Request, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os 
from fastapi.responses import RedirectResponse, JSONResponse
from get_methods import * 
from datetime import datetime
import hashlib

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

    #### если юзер просматривает свой профиль
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
            #### посты 
            cur.execute("SELECT * FROM posts WHERE who = ?", (id,))
            user_posts_raw = cur.fetchall()

            cur.execute("SELECT whom FROM like WHERE who = ?", (int_rowid,))
            liked_post_id = set(row[0] for row in cur.fetchall())

            user_posts = []
            for post in user_posts_raw:
                post_dict = {
                    "who": post[0],
                    "timestamp": post[1],
                    "text": post[2],
                    "likes": post[3],
                    "post_id": post[4],
                    "liked_by_viewer": post[4] in liked_post_id
                }
                user_posts.append(post_dict)

            #### понравившиеся
            cur.execute("""SELECT p.who, p.timestamp, p.text, p.likes, p.post_id,
                            u.name, u.login, u.avatar, CASE WHEN l2.whom IS 
                            NOT NULL THEN 1 ELSE 0 END AS liked_by_viewer
                            FROM like l1 JOIN posts p ON p.post_id = l1.whom
                            JOIN users u ON u.ROWID = p.who LEFT JOIN 
                            like l2 ON l2.whom = p.post_id AND l2.who = ?
                            WHERE l1.who = ?""", (int_rowid, id))
            user_likes = [
                {
                    "who": row[0],
                    "timestamp": row[1],
                    "text": row[2],
                    "likes": row[3],
                    "post_id": row[4],
                    "name": row[5],
                    "login": row[6],
                    "avatar": row[7],
                    "liked_by_viewer": bool(row[8])
                }
                for row in cur.fetchall()
            ]

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

    print(user_likes)
    return templates.TemplateResponse("profiles.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                     "path": user_data['path'], "rowid": user_data['rowid'],
                                                     "name_profile": name_profile, "login_profile": login_profile,
                                                     "path_profile": path_profile, "rowid_profile": rowid_profile,
                                                     "other_chats": other_chats, "other_subscribers": other_subscribers,
                                                     "posts": posts, "likes": likes, "sub": sub, "followers": followers,
                                                     "user_posts": user_posts, "user_likes": user_likes, "sub_block": sub_block})

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
            date = (datetime.now()).strftime("%Y.%m.%d %H:%M:%S")
            post_id = generate_post_id(rowid, date, text_post)
            cur.execute("INSERT INTO posts (who, timestamp, text, likes, post_id) VALUES (?, ?, ?, ?, ?)", (rowid, date, text_post, 0, post_id))
            cur.execute("UPDATE media SET posts = posts + 1 WHERE ROWID = ?", (rowid,))
            con.commit()
    return RedirectResponse(url=f"/{rowid}", status_code=303)

# редактирование поста
@profiles_router.post("/edit-post")
async def edit_post(request: Request,  post_id: str = Form(...), edited_text: str = Form(...)):
    rowid = request.session['user_data']['rowid']
    with sq.connect(db_path) as con:
            cur = con.cursor() 
            date = (datetime.now()).strftime("%Y.%m.%d %H:%M:%S")
            new_post_id = generate_post_id(rowid, date, edited_text)
            #### редактируем пост
            cur.execute("UPDATE posts SET timestamp = ?, text = ?, post_id = ? WHERE post_id = ?",
                (date, edited_text, new_post_id, post_id))
            con.commit()

    return RedirectResponse(url=f"/{rowid}", status_code=303) 

# удаление поста
@profiles_router.post("/delete-post")
async def delete_post(request: Request, post_id: str = Form(...)): 
     rowid = request.session['user_data']['rowid']
     with sq.connect(db_path) as con:
            cur = con.cursor()   
            #### удаляем пост
            cur.execute("DELETE FROM posts WHERE post_id = ?", (post_id,))
            cur.execute("UPDATE media SET posts = posts - 1 WHERE ROWID = ?", (rowid,))
            con.commit()
     return RedirectResponse(url=f"/{rowid}", status_code=303) 

# лайк поста
@profiles_router.post('/like-post')
async def like_post(request: Request, post_id: str = Form(...)): 
    rowid = request.session['user_data']['rowid']
    with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM like WHERE who = ? AND whom = ? LIMIT 1", (rowid, post_id))
            test_like = cur.fetchone()
            #### если пользователь не лайкал пост
            if not(test_like):
                cur.execute("UPDATE media SET likes = likes + 1 WHERE ROWID = ?", (rowid,))
                cur.execute("UPDATE posts SET likes = likes + 1 WHERE post_id = ?", (post_id,))
                cur.execute("INSERT INTO like (who, whom) VALUES (?, ?)", (rowid, post_id))
                liked = True
            #### если уже лайкал
            else:      
                cur.execute("SELECT who FROM posts WHERE post_id = ? LIMIT 1", (post_id,))
                id_user = cur.fetchone()[0]
                print(id_user, post_id)
                cur.execute("UPDATE media SET likes = likes - 1 WHERE ROWID = ?", (rowid,))
                cur.execute("UPDATE posts SET likes = likes - 1 WHERE post_id = ?", (post_id,))
                cur.execute("DELETE FROM like WHERE who = ? AND whom = ?", (rowid, post_id))
                liked = False
            #### обновлённое количество лайков
            cur.execute("SELECT likes FROM posts WHERE post_id = ?", (post_id,))
            likes = cur.fetchone()[0]
            con.commit()
            print(likes, post_id )
    return JSONResponse({"liked": liked, "likes": likes})

# подписка
@profiles_router.post('/add-friend')
async def sub_user(request: Request, user_id: int = Form(...)):
    rowid = request.session['user_data']['rowid']
    with sq.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM subscribers WHERE subscriber = ? AND author = ?", (rowid, user_id))
        test_sub = cur.fetchone()
        if not(test_sub):
            cur.execute("INSERT INTO subscribers (subscriber, author) VALUES (?, ?)", (rowid, user_id))
            cur.execute("UPDATE media SET followers = followers + 1 WHERE ROWID = ?", (user_id,))
            cur.execute("UPDATE media SET sub = sub + 1 WHERE ROWID = ?", (rowid,))
            status_sub = True 
        else: 
            cur.execute("DELETE FROM subscribers WHERE subscriber = ? AND author = ?", (rowid, user_id))
            cur.execute("UPDATE media SET followers = followers - 1 WHERE ROWID = ?", (user_id,))
            cur.execute("UPDATE media SET sub = sub - 1 WHERE ROWID = ?", (rowid,))
            status_sub = False 
        
    return JSONResponse(content={"status_sub": status_sub})

# генерация post_id
def generate_post_id(who: str, timestamp: str, text: str) -> str:
    base = f"{who}|{timestamp}|{text}"
    return hashlib.sha256(base.encode('utf-8')).hexdigest()

# проверка расширения
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
