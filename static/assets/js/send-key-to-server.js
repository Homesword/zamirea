async function sendPublicKeyToServer(publicKeyBase64, rowid) {

try {
    const response = await fetch(`/messages/save-public-key/${rowid}`, { 
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ public_key: publicKeyBase64 }),
    });

    if (!response.ok) {
        throw new Error("Ошибка при сохранении публичного ключа на сервере");
    }

} catch (error) {
    console.error("Ошибка:", error);
}

} 
