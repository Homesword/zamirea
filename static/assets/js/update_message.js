const userId = document.button.dataset.userId;

    async function poll() {
      try {
        const res = await fetch(`/messages/${userId}`);
        const data = await res.json();
        updateChat(data);
      } catch (e) {
        console.error("Ошибка:", e);
      } finally {
        setTimeout(poll, 3000); // снова вызвать через 3 секунды
      }
    }

    function updateChat(messages) {
      const chat = document.getElementById("chat");
      chat.innerHTML = ""; // очистить и перерисовать, или только новые добавить
      messages.forEach(msg => {
        const div = document.createElement("div");
        div.textContent = msg.text;
        chat.appendChild(div);
      })}