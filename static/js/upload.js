document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        title: document.getElementById('title').value,
        content: document.getElementById('content').value,
        category: document.getElementById('category').value
    };
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        if (result.success) {
            alert('Document uploaded successfully!');
            document.getElementById('upload-form').reset();
        } else {
            alert('Upload failed: ' + result.message);
        }
    } catch (error) {
        alert('Error uploading document: ' + error);
    }
}); 