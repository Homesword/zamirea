async function generateAndSaveKeys(rowid) {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: "RSA-OAEP",
            modulusLength: 2048,
            publicExponent: new Uint8Array([1, 0, 1]),
            hash: "SHA-256",
        },
        true,
        ["encrypt", "decrypt"]
    );

    // Экспортируем приватный ключ в формате PEM и сохраняем в localStorage
    const privateKey = await window.crypto.subtle.exportKey("pkcs8", keyPair.privateKey);
    const privateKeyBase64 = btoa(String.fromCharCode(...new Uint8Array(privateKey)));
    localStorage.setItem("privateKey", privateKeyBase64);

    // Экспортируем публичный ключ в формате PEM
    const publicKey = await window.crypto.subtle.exportKey("spki", keyPair.publicKey);
    const publicKeyBase64 = btoa(String.fromCharCode(...new Uint8Array(publicKey)));
    
    // Отправляем публичный ключ на сервер
    await sendPublicKeyToServer(publicKeyBase64, rowid);
}