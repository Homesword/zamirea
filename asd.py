import sqlite3 as sq
import os 

db_path = os.path.join(os.path.dirname(__file__), "zamirea_db.db") 

def get_other_chats(id):
     with sq.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(f"""SELECT DISTINCT 
            CASE WHEN id_sender < receiver_id THEN id_sender ELSE receiver_id END AS user1,
            CASE WHEN id_sender > receiver_id THEN id_sender ELSE receiver_id END AS user2
            FROM messages
            WHERE id_sender = ? OR receiver_id = ?;""", (id, id))
            all_id = cur.fetchall()
            list_infos = []
            for i in all_id:
                if i[0] == id:
                     cur.execute("SELECT name, avatar from users WHERE rowid = ?", (i[1],))


                     list_infos.append([i[1], cur.fetchone()])
                else:
                    cur.execute("SELECT name, avatar from users WHERE rowid = ?", (i[0],))
                    list_infos.append([i[0], cur.fetchone()])

            
            print(list_infos)

get_other_chats(1)