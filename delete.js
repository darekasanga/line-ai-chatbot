function deleteFile(filename) {
    const encodedFilename = encodeURIComponent(filename);
    const url = '/delete/' + encodedFilename;
    console.log("Attempting to delete:", filename);
    console.log("Encoded URL:", url);

    fetch(url, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            console.log("Server response:", data);
            if (data.status === "success") {
                alert("File deleted successfully!");
                location.reload();
            } else {
                alert("Failed to delete file: " + data.message);
                console.error("Delete failed:", data);
            }
        })
        .catch(error => {
            alert("Error during file deletion: " + error.message);
            console.error("Error during fetch request:", error);
        });
}
