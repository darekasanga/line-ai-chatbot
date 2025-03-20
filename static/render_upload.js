async function renderUploadPage() {
    const response = await fetch('/upload_page_json');
    const data = await response.json();
    const container = document.getElementById("upload-container");

    container.innerHTML = `
        <h2>${data.contents.body.contents[0].text}</h2>
        <form method="POST" enctype="multipart/form-data" action="/upload">
            <input type="file" name="file" required>
            <button type="submit">Upload</button>
            <button onclick="location.href='/list'">View Uploaded Files</button>
        </form>
    `;
}

window.onload = renderUploadPage;
