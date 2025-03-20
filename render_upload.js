async function renderUploadPage() {
    const response = await fetch('/upload.html');
    const data = await response.json();
    const container = document.getElementById("upload-container");

    container.innerHTML = `
        <h2>${data.contents.body.contents[0].text}</h2>
        <p>${data.contents.body.contents[1].contents[0].text}</p>
        <form method="POST" enctype="multipart/form-data" action="/upload">
            <input type="file" name="file" accept="image/*" required>
            <button type="submit">${data.contents.body.contents[2].contents[0].action.label}</button>
            <button type="button" onclick="location.href='/list'">${data.contents.body.contents[2].contents[1].action.label}</button>
        </form>
    `;
}

window.onload = renderUploadPage;
