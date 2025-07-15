import os
import sqlite3 as sq

db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db") 

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
                if i[0] == id:
                    cur.execute("SELECT name, avatar from users WHERE rowid = ?", (i[1],))
                    list_infos.insert(0, [i[1], cur.fetchone()])
                else:
                    cur.execute("SELECT name, avatar from users WHERE rowid = ?", (i[0],))
                    list_infos.insert(0, [i[0], cur.fetchone()])
            
            return list_infos
    
def get_subscribers(id: int):
     with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT author from subscribers WHERE subscriber = ?", (id,))
            id_subs = cur.fetchall() # id тех, на кого юзер подписан
            if not id_subs: return 0
            all_subs = []
            for i in id_subs:
                cur.execute("SELECT name, avatar from users WHERE ROWID = ?", (i[0],))
                all_subs.insert(0, [i[0], cur.fetchone()])
            return all_subs
     