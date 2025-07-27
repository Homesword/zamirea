import sqlite3 as sq
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
import os 
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
from get_methods import * 

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
    if not(request.session.get("user_logged")):
        return RedirectResponse(url="/")
    return RedirectResponse(url="/messages/1", status_code=303)


@chat_router.get("/messages/{id}") 
async def messages(request: Request, id: str):
    if not(request.session.get("user_logged")):
        return RedirectResponse(url="/")
    try:
        rowid = request.session['user_data']['rowid']
        if rowid == int(id): # чтобы не писал сам себе
            return RedirectResponse(url="/", status_code=303) 
        
        user_data = request.session['user_data']

        #### есть ли ключи и данные о получателе
        with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM keys WHERE id = ? LIMIT 1", (rowid,))
            if not cur.fetchone():
                not_key = 1
            else:
                not_key = 0
            cur.execute("SELECT * FROM users WHERE ROWID = ? LIMIT 1", (id,))
            recipient_value = cur.fetchone()

        #### правый блок
        int_rowid = int(rowid)
        other_chats = get_other_chats(int_rowid)
        other_subscribers = get_subscribers(int_rowid)

        return templates.TemplateResponse("messages.html", {"request": request, "name": user_data['name'], "login": user_data['login'],
                                                    "path": user_data['path'].replace('\\', '/').strip(), "rowid": int(user_data['rowid']), "not_key": not_key, 
                                                    "id_recipient": id, "recipient_value": recipient_value, 
                                                    "other_chats": other_chats,
                                                    "other_subscribers": other_subscribers})
    except Exception as e:
        print("Ошибка в переписке:", e)
        raise HTTPException(status_code=500, detail="Ошибка сервера")



@chat_router.get("/messages/{id}/data")
async def get_messages_data(request: Request, id: int, page: int = Query(1)):
    rowid = int(request.session['user_data']['rowid'])
    result = get_message(rowid, id, page)

    # распаковываем данные
    status = result[0]
    messages_raw = result[1]
    user_info = result[2]

    # преобразуем в список словарей
    messages = []
    for msg in messages_raw:
        sender_id, receiver_id, encrypted_text, timestamp, _ = msg
        messages.append({
            "is_my": sender_id == rowid,
            "text": encrypted_text,
            "time": timestamp
        })
    return JSONResponse(content=messages)
     

# сохранение публичного ключа пользователя
@chat_router.post("/save-public-key/{rowid}") 
def save_public_key(request: PublicKeyRequest, rowid: str):
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
            return RedirectResponse(url=f"/messages/{rowid}", status_code=303)
        #### сообщение для отправки
        message = messagerequest.text_message.encode()
        if message.decode().strip() == "": # если пустое сообщение / пробелы и т.п.
            return RedirectResponse(url=f"/messages/{rowid}", status_code=303)

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
    
    # общий механизм отправки
    with sq.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM keys WHERE id = ?", (rowid,))
        if not cur.fetchone():
            print(f"Ошибка: пользователь с rowid={rowid} не найден")
            return
    fake_request = type('', (), {'session': {'user_data': {'rowid': '1'}}})()
    send_message(fake_request, rowid, message_request)


# переписка 
def get_message(rowid, id, page):
    with sq.connect(db_path) as con:
        cur = con.cursor()
        not_key = 1

        #### есть ли ключи
        cur.execute("SELECT 1 FROM keys WHERE id = ? LIMIT 1", (rowid,))
        if not cur.fetchone():
            return [not_key, [], ""]

        cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (id,))
        recipient_key = cur.fetchone()
        if not recipient_key:
            return RedirectResponse(url="/", status_code=303)
        not_key = 0
        
        offset_value = (page - 1) * 10
        cur.execute("""SELECT * FROM messages
                    WHERE ((id_sender = ? AND receiver_id = ? AND type = 1) OR
                    (id_sender = ? AND receiver_id = ? AND type = 0))
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?""", (rowid, id, id, rowid, 10, offset_value))
        all_messages = cur.fetchall()

        #### информация о получателе
        cur.execute("SELECT * FROM users WHERE ROWID = ? LIMIT 1", (id,))
        recipient_value = cur.fetchone()

        return [not_key, all_messages, recipient_value]
