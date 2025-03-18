from datetime import datetime

# Пример списка сообщений (дата в строковом формате)
messages = [
    ["Привет!","2025.03.18 14:48:34"],
    ["Как дела?","2025.03.18 14:45:12"],
    ["Что нового?", "2025.03.18 14:50:00"],
]

# Сортировка сообщений по дате
messages_sorted = sorted(messages, key=lambda msg: datetime.strptime(msg[1], "%Y.%m.%d %H:%M:%S"))

# Вывод
for msg in messages_sorted:
    print(msg)
