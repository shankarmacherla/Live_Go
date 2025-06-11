/**
 * Shared Image Upload Functionality 
 * This script provides shared functionality for handling image uploads
 * across both automatic and manual detection pages
 */

// Track uploaded images in session storage
function saveUploadedImage(imageDataUrl, fileName) {
    sessionStorage.setItem('lastUploadedImage', imageDataUrl);
    sessionStorage.setItem('lastUploadedImageName', fileName);
}

// Get last uploaded image from session storage
function getLastUploadedImage() {
    return {
        dataUrl: sessionStorage.getItem('lastUploadedImage'),
        fileName: sessionStorage.getItem('lastUploadedImageName')
    };
}

// Apply last uploaded image to page if available
function applyLastUploadedImage() {
    const { dataUrl, fileName } = getLastUploadedImage();

    if (!dataUrl) return;

    // Auto detect page
    const autoDetectPreview = document.getElementById('upload-preview');
    const autoDetectArea = document.getElementById('upload-area');
    const autoFileNameDisplay = document.getElementById('file-name-display');

    // Manual detect page
    const manualPreview = document.getElementById('manual-upload-preview');
    const manualArea = document.getElementById('manual-upload-area');

    // Apply to auto detect page if elements exist
    if (autoDetectPreview && autoDetectArea) {
        autoDetectPreview.src = dataUrl;
        autoDetectPreview.style.display = 'block';
        autoDetectArea.classList.add('has-file');

        if (autoFileNameDisplay) {
            autoFileNameDisplay.textContent = fileName || 'Uploaded image';
        }
    }

    // Apply to manual detect page if elements exist
    if (manualPreview && manualArea) {
        manualPreview.src = dataUrl;
        manualPreview.style.display = 'block';
        manualArea.classList.add('has-file');
    }
}

// Enhanced file preview display with shared storage
function enhancedDisplayFilePreview(file, previewElement, uploadAreaElement, fileNameElement = null) {
    if (!file.type.match('image.*')) {
        console.error('Please select an image file');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        // Update the preview element
        if (previewElement) {
            previewElement.src = e.target.result;
            previewElement.style.display = 'block';
        }

        // Mark upload area as having a file
        if (uploadAreaElement) {
            uploadAreaElement.classList.add('has-file');
        }

        // Update file name display if provided
        if (fileNameElement) {
            fileNameElement.textContent = file.name;
        }

        // Save to session storage for cross-page use
        saveUploadedImage(e.target.result, file.name);
    };

    reader.readAsDataURL(file);
}