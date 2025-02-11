document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const statusDiv = document.getElementById('upload-status');
    const submitButton = document.querySelector('.upload-button');
    
    // Validate content length
    const content = document.getElementById('content').value;
    if (content.length < 50) {
        statusDiv.innerHTML = '<div style="color: #dc3545;">Content must be at least 50 characters long</div>';
        return;
    }
    
    const formData = {
        title: document.getElementById('title').value,
        content: content,
        category: document.getElementById('category').value
    };
    
    try {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        
        const response = await fetch('/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        if (result.success) {
            statusDiv.innerHTML = '<div style="color: #28a745;"><i class="fas fa-check-circle"></i> Document uploaded successfully!</div>';
            document.getElementById('upload-form').reset();
        } else {
            statusDiv.innerHTML = `<div style="color: #dc3545;"><i class="fas fa-exclamation-circle"></i> Upload failed: ${result.message}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div style="color: #dc3545;"><i class="fas fa-exclamation-circle"></i> Error uploading document: ${error}</div>`;
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Upload Document';
    }
}); 