import sqlite3 as sq
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
import os 
from fastapi.responses import RedirectResponse
from datetime import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64


chat_router = APIRouter()
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)
db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db") 


class PublicKeyRequest(BaseModel):
    public_key: str

class MessageRequest(BaseModel):
    text_message: str
    is_admin: bool = False  # флаг, указывающий что сообщение от админа


@chat_router.get("/messages")
async def messages_redirect(request: Request):
    return RedirectResponse(url="/messages/1", status_code=303)


@chat_router.get("/messages/{id}") 
async def messages(request: Request, id: str):
    try:
        rowid = request.session['user_data']['rowid']
        # проверка, чтобы не писал сам себе
        if rowid == id:
            return RedirectResponse(url="/", status_code=303) 
        user_data = request.session['user_data']
        not_key, now_sender, recipient, recipient_value = get_message(rowid=rowid, id=id)

        ############ ИТОГОВАЯ ПЕРЕПИСКИ ПО ДАТАМ 
        messages_in_chat = now_sender + recipient
        messages_sorted = sorted(messages_in_chat, key=lambda msg: datetime.strptime(msg[3], "%Y.%m.%d %H:%M:%S"))

        ############ ДРУГИЕ ЧАТЫ
        other_chats = get_other_chats(int(rowid))
        return templates.TemplateResponse("messages.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                    "path": user_data['path'], "rowid": int(user_data['rowid']), "not_key": not_key, 
                                                    "id_recipient":id, "recipient_value": recipient_value, 
                                                    "messages_sorted":messages_sorted, "other_chats": other_chats})
    except Exception as e:
        print("Ошибка в переписке:", e)
        raise HTTPException(status_code=500, detail="Ошибка сервера")
        

# сохранение публичного ключа пользователя
@chat_router.post("/save-public-key/{rowid}") 
def save_public_key(request: PublicKeyRequest, rowid: str):
    # проверка если чел попробовал сделать пост запрос уже имея себя в БД
    try:
        key_bytes = base64.b64decode(request.public_key)
        public_key = serialization.load_der_public_key(key_bytes)
        public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""INSERT INTO keys (id, key) 
                        VALUES (?, ?)""", (rowid, public_key_pem))
            con.commit()

        send_admin_message(rowid) # отправляем от имени админа приветственное сообщение
        return RedirectResponse(url="/messages", status_code=303) 
    except Exception as e:
       print("Ошибка в сохранении ключа: ", e)
       return RedirectResponse(url="/", status_code=303) 


# отправка сообщения 
########### ДОПИСАТЬ
@chat_router.post("/send-message/{rowid}")
def send_message(request: Request, rowid: str, messagerequest: MessageRequest):
    try:
        if rowid == '1':  # админу нельзя отправлять сообщения
            return RedirectResponse(url="/messages/1", status_code=303)

        date = datetime.now()
        with sq.connect(db_path) as con:
            cur = con.cursor()
            
            # Определяем ID отправителя (админ или текущий пользователь)
            sender_id = '1' if messagerequest.is_admin else request.session['user_data']['rowid']
            
            # ключ получателя
            cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (rowid,))
            recipient_key_pem = cur.fetchone()
            
            if not recipient_key_pem:
                return RedirectResponse(url="/", status_code=303)

            # загружаем публичный ключ получателя
            recipient_public_key = serialization.load_pem_public_key(
                recipient_key_pem[0].encode(),
                backend=default_backend()
            )

            # ключ отправителя (для админа используем его же ключ как получателя)
            cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (sender_id,))
            sender_key_pem = cur.fetchone()

            if not sender_key_pem:
                return RedirectResponse(url="/", status_code=303)

            sender_public_key = serialization.load_pem_public_key(
                sender_key_pem[0].encode(),
                backend=default_backend()
            )

            # сообщение для отправки
            message = messagerequest.text_message.encode()

            # Шифруем для получателя
            encode_message1 = base64.b64encode(recipient_public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )).decode()
            
            # Шифруем копию ключом отправителя (админа)
            encode_message2 = base64.b64encode(sender_public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )).decode()
        
            # Вставляем оба сообщения
            cur.executemany(
                """INSERT INTO messages (id_sender, receiver_id, message, timestamp, type) 
                   VALUES (?, ?, ?, ?, ?)""", 
                [
                    (sender_id, rowid, encode_message1, date.strftime("%Y.%m.%d %H:%M:%S"), 0),
                    (sender_id, rowid, encode_message2, date.strftime("%Y.%m.%d %H:%M:%S"), 1)
                ]
            )
            con.commit()
            
    except Exception as e:
        print("Ошибка в сохранении сообщения: ", e)
        return RedirectResponse(url="/", status_code=303)


# отправка приветственного сообщения от администратора
def send_admin_message(rowid):
    admin_message = """Приветствуем тебя в ZaMiReA!
    Не забудь ознакомиться с политикой соглашения) by Homesword, тг: https://t.me/Homesword"""
    
    # Создаем запрос с флагом is_admin=True
    message_request = MessageRequest(
        text_message=admin_message,
        is_admin=True
    )
    
    # Используем общий механизм отправки
    with sq.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM keys WHERE id = ?", (rowid,))
        if not cur.fetchone():
            print(f"Ошибка: пользователь с rowid={rowid} не найден")
            return
    fake_request = type('', (), {'session': {'user_data': {'rowid': '1'}}})()
    send_message(fake_request, rowid, message_request)


# переписка 
def get_message(rowid, id):
    with sq.connect(db_path) as con:
            not_key = 1
            cur = con.cursor()
            cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (rowid,))
            now_sender, recipient, recipient_value = '', '', ''
            key_sender = cur.fetchone() # если у человека есть ключи
            if key_sender:
                ############ ПРОВЕРКА, ЧТО ЧЕЛ КОТОРОМУ МЫ ПИШЕМ СУЩЕСТВУЕТ
                cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (id,))
                recipient_key = cur.fetchone()
                if not(recipient_key):
                    return RedirectResponse(url="/", status_code=303) 
                ############ ПЕРЕПИСКА
                not_key = 0
                # берём с типом 0, тк мы можем расшифровать только то, что было закодировано нашим публичным ключом.
                cur.execute("""SELECT * FROM messages WHERE id_sender = ? AND receiver_id = ? AND type = ?""", (rowid, id, 1))
                now_sender = cur.fetchall() # вся история переписки с точки зрения отправителя 
                # берём с типом 1, тк мы можем расшифровать только то, что было закодировано нашим публичным ключом.
                cur.execute(f"""SELECT * FROM messages WHERE id_sender = ? AND receiver_id = ? AND type = ?""", (id, rowid, 0))
                recipient = cur.fetchall() # вся история переписки с челом с точки зрения получателя
                cur.execute(f"SELECT * FROM users LIMIT 1 OFFSET {int(id)-1}")
                recipient_value = cur.fetchone()
                return [not_key, now_sender, recipient, recipient_value]
            return [1, "", "", ""]
            

def get_other_chats(id: int):
     with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(f"""SELECT DISTINCT 
            CASE WHEN id_sender < receiver_id THEN id_sender ELSE receiver_id END AS user1,
            CASE WHEN id_sender > receiver_id THEN id_sender ELSE receiver_id END AS user2
            FROM messages
            WHERE id_sender = ? OR receiver_id = ?;""", (id, id))
            all_id = cur.fetchall() 
            list_infos = []
            # итоговый список с id и данными юзера
            for i in all_id:
                print(id, type(id))
                if i[0] == id:
                    cur.execute("SELECT name, avatar from users WHERE rowid = ?", (i[1],))
                    list_infos.append([i[1], cur.fetchone()])
                else:
                    cur.execute("SELECT name, avatar from users WHERE rowid = ?", (i[0],))
                    list_infos.append([i[0], cur.fetchone()])
            
            return list_infos