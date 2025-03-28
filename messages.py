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




        return templates.TemplateResponse("messages.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                    "path": user_data['path'], "rowid": int(user_data['rowid']), "not_key": not_key, 
                                                    "now_sender":now_sender, "recipient":recipient, "recipient_value": recipient_value, 
                                                    "messages_sorted":messages_sorted})
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
def send_message(request: Request, rowid: str):
    try:
        date = datetime.now()
        with sq.connect(db_path) as con:
            cur = con.cursor()
            
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

            # ключ отправителя
            cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (request.session['user_data']['rowid'],))
            sender_key_pem = cur.fetchone()

            if not sender_key_pem:
                return RedirectResponse(url="/", status_code=303)

            sender_public_key = serialization.load_pem_public_key(
                sender_key_pem[0].encode(),
                backend=default_backend()
            )

            # сообщение для отправки
            message = "Привет, это тестовое сообщение!".encode()

            encode_message1 = base64.b64encode(recipient_public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )).decode()
            
            cur.execute("""INSERT INTO messages (id_sender, receiver_id, message, timestamp, type) 
                            VALUES (?, ?, ?, ?, ?)""", (request.session['user_data']['rowid'], rowid, encode_message1,
                                                            date.strftime("%Y.%m.%d %H:%M:%S"), 0))
            # получаем копию 
            # тут сообщение закодированное публичным ключом отправителя
            encode_message2 = base64.b64encode(sender_public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )).decode()
        
            cur.execute("""INSERT INTO messages (id_sender, receiver_id, message, timestamp, type) 
                            VALUES (?, ?, ?, ?, ?)""", (request.session['user_data']['rowid'], rowid, encode_message2,
                                                            date.strftime("%Y.%m.%d %H:%M:%S"), 1))
            
    except Exception as e:
         print("Ошибка в сохранении сообщения: ", e)
         return RedirectResponse(url="/", status_code=303) 


# отправка приветственного сообщения от администратора
def send_admin_message(rowid):
    with sq.connect(db_path) as con:
        cur = con.cursor()

        cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (rowid,))
        recipient_key_pem = cur.fetchone()

        if not recipient_key_pem:
            print(f"Ошибка: не найден публичный ключ для rowid={rowid}")
            return

        # загружаем публичный ключ из PEM-формата
        recipient_public_key = serialization.load_pem_public_key(
            recipient_key_pem[0].encode(),  
            backend=default_backend()
        )

        # шифруем сообщение
        message = f"""Приветствуем тебя в ZaMiReA!
        Не забудь ознакомиться с политикой соглашения) by Homesword, тг: https://t.me/Homesword""".encode()

        encode_message = base64.b64encode(recipient_public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )).decode()

        # сохраняем в БД сообщение от админа
        date = datetime.now()
        cur.execute("""INSERT INTO messages (id_sender, receiver_id, message, timestamp, type) 
                       VALUES (?, ?, ?, ?, ?)""", (1, rowid, encode_message,
                                                   date.strftime("%Y.%m.%d %H:%M:%S"), 1))
        con.commit()


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
                cur.execute("""SELECT * FROM messages WHERE id_sender = ? AND receiver_id = ? AND type = ?""", (rowid, id, 0))
                now_sender = cur.fetchall() # вся история переписки с точки зрения отправителя 
                # берём с типом 1, тк мы можем расшифровать только то, что было закодировано нашим публичным ключом.
                cur.execute(f"""SELECT * FROM messages WHERE id_sender = ? AND receiver_id = ? AND type = ?""", (id, rowid, 1))
                recipient = cur.fetchall() # вся история переписки с челом с точки зрения получателя
                cur.execute(f"SELECT * FROM users LIMIT 1 OFFSET {int(id)-1}")
                recipient_value = cur.fetchone()
                return [not_key, now_sender, recipient, recipient_value]
            return [1, "", "", ""]
            