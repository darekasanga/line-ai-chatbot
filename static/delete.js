function deleteFile(filename) {
    fetch(`/delete/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                alert("File deleted successfully!");
                location.reload();
            } else {
                alert("Failed to delete file: " + data.message);
            }
        })
        .catch(error => {
            alert("Error during file deletion: " + error.message);
        });
}
