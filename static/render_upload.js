async function renderUploadPage() {
    try {
        const response = await fetch('/upload_page_json');
        const data = await response.json();
        const container = document.getElementById("upload-container");

        const title = data.contents.body.contents[0].text;
        const uploadText = data.contents.body.contents[1].contents[0].text;
        const uploadLabel = data.contents.body.contents[2].contents[0].action.label;
        const viewLabel = data.contents.body.contents[2].contents[1].action.label;

        container.innerHTML = `
            <h2>${title}</h2>
            <p>${uploadText}</p>
            <form method="POST" enctype="multipart/form-data" action="/upload">
                <input type="file" name="file" required>
                <button type="submit">${uploadLabel}</button>
                <button onclick="location.href='/list'">${viewLabel}</button>
            </form>
        `;
    } catch (error) {
        console.error("Error rendering upload page:", error);
    }
}

window.onload = renderUploadPage;
