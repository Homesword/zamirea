function pemToDer(pem) {
    const base64String = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
    const binaryDer = atob(base64String);
    const derArray = new Uint8Array(binaryDer.length);
    for (let i = 0; i < binaryDer.length; i++) {
        derArray[i] = binaryDer.charCodeAt(i);
    }
    return derArray.buffer;
}
