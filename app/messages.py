import sqlite3 as sq
from fastapi import APIRouter, Request, HTTPException, Query, WebSocket, WebSocketDisconnect
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
from typing import Dict

chat_router = APIRouter(prefix="/messages")
path_templates = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=path_templates)
db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db")


class PublicKeyRequest(BaseModel):
    public_key: str


class MessageRequest(BaseModel):
    text_message: str
    is_admin: bool = False  # флаг, указывающий что сообщение от админа


# ----------------- WebSocket Connection Manager -----------------
class ConnectionManager:
    def __init__(self):
        # room_id -> { user_id: WebSocket, ... }
        self.active_connections: Dict[str, Dict[int, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][int(user_id)] = websocket

    def disconnect(self, room_id: str, user_id: int):
        if room_id in self.active_connections and int(user_id) in self.active_connections[room_id]:
            try:
                del self.active_connections[room_id][int(user_id)]
            except KeyError:
                pass
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: str, room_id: str, sender_id: int):
        """
        Системные/общие сообщения: encrypted=False
        """
        if room_id in self.active_connections:
            for uid, connection in list(self.active_connections[room_id].items()):
                payload = {
                    "text": message,
                    "is_self": uid == int(sender_id),
                    "encrypted": False
                }
                try:
                    await connection.send_json(payload)
                except Exception:
                    self.disconnect(room_id, uid)

    async def broadcast_personalized(self, room_id: str, sender_id: int, messages_map: Dict[int, str]):
        """
        Отправляет персонализированные (зашифрованные) строки каждому подключённому пользователю.
        messages_map: { user_id: base64_encrypted_text, ... }
        """
        if room_id not in self.active_connections:
            return

        for uid, connection in list(self.active_connections[room_id].items()):
            text_for_user = messages_map.get(int(uid))
            if text_for_user is None:
                continue
            payload = {
                "text": text_for_user,
                "is_self": int(uid) == int(sender_id),
                "encrypted": True
            }
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(room_id, uid)


manager = ConnectionManager()
# ----------------------------------------------------------------


@chat_router.get("/")
async def messages_redirect(request: Request):
    if not (request.session.get("user_logged")):
        return RedirectResponse(url="/")
    return RedirectResponse(url="/messages/1", status_code=303)


@chat_router.get("/{id}")
async def messages(request: Request, id: str):
    if not (request.session.get("user_logged")):
        return RedirectResponse(url="/")

    flag = True
    int_id = int(id)
    if not (int_id < 1):
        with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT MAX(ROWID) FROM users")
            if not (int_id > int(cur.fetchone()[0])):
                flag = False
    if flag:
        return RedirectResponse(url="/")

    try:
        rowid = request.session['user_data']['rowid']
        if (rowid == int_id) and rowid != 1:
            return RedirectResponse(url="/", status_code=303)

        user_data = request.session['user_data']

        with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM keys WHERE id = ? LIMIT 1", (rowid,))
            not_key = 0 if cur.fetchone() else 1
            cur.execute("SELECT * FROM users WHERE ROWID = ? LIMIT 1", (id,))
            recipient_value = cur.fetchone()

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


@chat_router.get("/{id}/data")
async def get_messages_data(request: Request, id: int, page: int = Query(1)):
    rowid = int(request.session['user_data']['rowid'])
    result = get_message(rowid, id, page)

    status = result[0]
    messages_raw = result[1]
    user_info = result[2]

    messages = []
    for msg in messages_raw:
        sender_id, receiver_id, encrypted_text, timestamp, _ = msg
        messages.append({
            "is_my": sender_id == rowid,
            "text": encrypted_text,
            "time": timestamp
        })
    return JSONResponse(content=messages)


@chat_router.post("/save-public-key/{rowid}")
async def save_public_key(request: PublicKeyRequest, rowid: str):
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

        await send_admin_message(rowid)
        return RedirectResponse(url="/messages", status_code=303)
    except Exception as e:
        print("Ошибка в сохранении ключа: ", e)
        return RedirectResponse(url="/", status_code=303)


@chat_router.post("/send-message/{rowid}")
async def send_message(request: Request, rowid: str, messagerequest: MessageRequest):
    try:
        if rowid == '1':
            return RedirectResponse(url=f"/messages/{rowid}", status_code=303)

        message = messagerequest.text_message.encode()
        if message.decode().strip() == "":
            return RedirectResponse(url=f"/messages/{rowid}", status_code=303)

        date = datetime.now()

        sender_id = '1' if messagerequest.is_admin else request.session['user_data']['rowid']
        sender_id = int(sender_id)
        recipient_id = int(rowid)

        with sq.connect(db_path) as con:
            cur = con.cursor()

            cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1", (rowid,))
            recipient_key_pem = cur.fetchone()
            if not recipient_key_pem:
                return RedirectResponse(url="/", status_code=303)

            recipient_public_key = serialization.load_pem_public_key(
                recipient_key_pem[0].encode(),
                backend=default_backend()
            )

            cur.execute("SELECT key FROM keys WHERE id = ? LIMIT 1",
                        (str(sender_id),))
            sender_key_pem = cur.fetchone()
            if not sender_key_pem:
                return RedirectResponse(url="/", status_code=303)

            sender_public_key = serialization.load_pem_public_key(
                sender_key_pem[0].encode(),
                backend=default_backend()
            )

            encode_message1 = base64.b64encode(recipient_public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )).decode()

            encode_message2 = base64.b64encode(sender_public_key.encrypt(
                message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )).decode()

            cur.executemany(
                """INSERT INTO messages (id_sender, receiver_id, message, timestamp, type) 
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (sender_id, recipient_id, encode_message1,
                     date.strftime("%Y.%m.%d %H:%M:%S"), 0),
                    (sender_id, recipient_id, encode_message2,
                     date.strftime("%Y.%m.%d %H:%M:%S"), 1)
                ]
            )
            con.commit()

        room_id = f"{min(sender_id, recipient_id)}_{max(sender_id, recipient_id)}"

        messages_map = {
            sender_id: encode_message2,
            recipient_id: encode_message1
        }

        try:
            await manager.broadcast_personalized(room_id, sender_id, messages_map)
        except Exception as e:
            print("Ошибка при рассылке WebSocket:", e)

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        print("Ошибка в сохранении сообщения: ", e)
        return RedirectResponse(url="/", status_code=303)


async def send_admin_message(rowid):
    admin_message = """Приветствуем тебя в ZaMiReA!
Не забудь ознакомиться с политикой соглашения) by Homesword, тг: https://t.me/Homesword"""

    message_request = MessageRequest(
        text_message=admin_message,
        is_admin=True
    )

    with sq.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM keys WHERE id = ?", (rowid,))
        if not cur.fetchone():
            print(f"Ошибка: пользователь с rowid={rowid} не найден")
            return

    fake_request = type('', (), {'session': {'user_data': {'rowid': '1'}}})()
    await send_message(fake_request, rowid, message_request)


def get_message(rowid, id, page):
    with sq.connect(db_path) as con:
        cur = con.cursor()
        not_key = 1

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

        cur.execute("SELECT * FROM users WHERE ROWID = ? LIMIT 1", (id,))
        recipient_value = cur.fetchone()

        return [not_key, all_messages, recipient_value]


@chat_router.websocket("/ws/{room_id}/{username}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str, user_id: int):
    await manager.connect(websocket, room_id, user_id)
    try:
        while True:
            try:
                _ = await websocket.receive_text()
            except WebSocketDisconnect:
                raise
    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)
