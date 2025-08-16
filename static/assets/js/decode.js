function base64ToArrayBuffer(base64) {
    // убираем все переносы строк и пробелы
    base64 = base64.replace(/-----.*-----/g, "").replace(/\s+/g, "");
    try {
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    } catch (e) {
        console.error("❌ Невалидная base64-строка:", base64);
        throw e;
    }
}

async function decryptMessage(encryptedMessageBase64) {
    try {
        if (!encryptedMessageBase64 || encryptedMessageBase64.length < 10) {
            throw new Error("Зашифрованное сообщение пустое или слишком короткое");
        }

        // получаем приватный ключ из LocalStorage
        let privateKeyPem = localStorage.getItem("privateKey");
        if (!privateKeyPem) {
            throw new Error("❌ Приватный ключ не найден в LocalStorage!");
        }

        // конвертируем PEM в бинарный формат
        let privateKeyDer = base64ToArrayBuffer(privateKeyPem);

        // импортируем приватный ключ
        let privateKey = await window.crypto.subtle.importKey(
            "pkcs8",
            privateKeyDer,
            { name: "RSA-OAEP", hash: "SHA-256" },
            true,
            ["decrypt"]
        );

        // декодируем зашифрованное сообщение
        let encryptedData = base64ToArrayBuffer(encryptedMessageBase64);

        // расшифровка
        let decryptedBuffer = await window.crypto.subtle.decrypt(
            { name: "RSA-OAEP" },
            privateKey,
            encryptedData
        );

        return new TextDecoder().decode(decryptedBuffer);

    } catch (error) {
        console.error("⚠ Ошибка расшифровки:", error);
        return "[Ошибка расшифровки]";
    }
}
