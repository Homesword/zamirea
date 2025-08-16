let ws = null;

function initWebSocket(chatId, username, rowid) {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(`${protocol}${window.location.host}/ws/${chatId}/${username}/${rowid}`);

    ws.onopen = () => {
        console.log("✅ WebSocket подключён");
    };

    ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat ${msg.is_self ? 'chat-left' : ''}`;

        const avatarSrc = msg.is_self ? myAvatar : recipientAvatar;
        const profileLink = msg.is_self ? `/${rowid}` : `/${chatId}`;

        messageDiv.innerHTML = `
            <div class="chat-avatar">
                <a href="${profileLink}" class="d-inline-block">
                    <img src="${avatarSrc}" width="50" height="50" class="rounded-circle" alt="avatar">
                </a>
            </div>
            <div class="chat-body">
                <div class="chat-message">
                    <span class="message-content">${msg.text}</span>
                    <span class="time d-block">${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        `;

        document.getElementById('chat-container').appendChild(messageDiv);
        forceScrollToBottom();
    };

    ws.onclose = () => {
        console.warn("⚠️ WebSocket закрыт. Переподключение через 3 секунды...");
        setTimeout(() => initWebSocket(chatId, username, rowid), 3000);
    };
}

async function saveInput(rowid) {
    event.preventDefault();
    const inputElement = document.getElementById("sendMessageToServer");
    
    const userText = inputElement.value.trim();

    if (!userText) {
        console.log("Попытка отправить пустоту.");
        return;
    }

    try {
        // отправка в базу
        const response = await fetch(`/messages/send-message/${rowid}`, { 
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text_message: userText }),
        });

        if (!response.ok) {
            throw new Error("Ошибка при передаче сообщения в базу.");
        }

        // отправка по WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(userText);
        } else {
            console.warn("⚠️ WebSocket не подключен, сообщение будет видно только после перезагрузки");
        }

        // очистка поля
        inputElement.value = "";

    } catch (error) {
        console.error("Ошибка:", error);
    }
}
