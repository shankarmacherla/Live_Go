/**
 * Image Enhancement Tools
 * Provides tools to enhance component images
 */

let selectedImage = null;
let originalImageData = null;
let canvas = null;
let ctx = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize enhancement tools if available on page
    initEnhancementTools();
});

// Initialize image enhancement tools
function initEnhancementTools() {
    const enhancementTools = document.querySelectorAll('.enhancement-tool');
    const enhancementPreview = document.getElementById('enhancement-preview');

    if (!enhancementTools.length) return;

    // Set up image selection for enhancement
    const componentImages = document.querySelectorAll('.component-select-image');
    componentImages.forEach(img => {
        img.addEventListener('click', function() {
            selectImageForEnhancement(this);
        });
    });

    // Initialize canvas for image processing
    canvas = document.getElementById('enhancement-canvas');
    if (canvas) {
        ctx = canvas.getContext('2d');
    }

    // Setup enhancement tool event listeners
    enhancementTools.forEach(tool => {
        tool.addEventListener('click', function() {
            const toolType = this.getAttribute('data-tool');
            if (!selectedImage) {
                alert('Please select an image to enhance first');
                return;
            }

            applyEnhancement(toolType);
        });
    });

    // Reset button
    const resetButton = document.getElementById('reset-enhancement');
    if (resetButton) {
        resetButton.addEventListener('click', resetEnhancement);
    }

    // Save button
    const saveButton = document.getElementById('save-enhancement');
    if (saveButton) {
        saveButton.addEventListener('click', saveEnhancement);
    }
}

// Select an image for enhancement
function selectImageForEnhancement(imgElement) {
    // Clear previous selection
    document.querySelectorAll('.component-select-image').forEach(img => {
        img.classList.remove('selected-for-enhancement');
    });

    // Mark as selected
    imgElement.classList.add('selected-for-enhancement');
    selectedImage = imgElement;

    // Setup canvas with the selected image
    if (canvas && ctx) {
        // Load image to canvas
        const img = new Image();
        img.onload = function() {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            // Store original image data for reset
            originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

            // Show enhancement panel
            const enhancementPanel = document.getElementById('enhancement-panel');
            if (enhancementPanel) {
                enhancementPanel.classList.remove('d-none');
            }
        };
        img.src = imgElement.src;
    }
}

// Apply enhancement to the selected image
function applyEnhancement(toolType) {
    if (!canvas || !ctx || !originalImageData) return;

    // Get image data
    let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    let data = imageData.data;

    switch(toolType) {
        case 'brightness':
            // Simple brightness adjustment
            for (let i = 0; i < data.length; i += 4) {
                data[i] = Math.min(255, data[i] * 1.2);     // Red
                data[i+1] = Math.min(255, data[i+1] * 1.2); // Green
                data[i+2] = Math.min(255, data[i+2] * 1.2); // Blue
            }
            break;

        case 'contrast':
            // Simple contrast adjustment
            const factor = 25.5; // Increase contrast by 10%
            const intercept = 128 * (1 - factor / 255);

            for (let i = 0; i < data.length; i += 4) {
                data[i] = Math.min(255, Math.max(0, factor * (data[i] / 255) + intercept));
                data[i+1] = Math.min(255, Math.max(0, factor * (data[i+1] / 255) + intercept));
                data[i+2] = Math.min(255, Math.max(0, factor * (data[i+2] / 255) + intercept));
            }
            break;

        case 'sharpen':
            // Apply a simple sharpening filter
            let tempCanvas = document.createElement('canvas');
            tempCanvas.width = canvas.width;
            tempCanvas.height = canvas.height;
            let tempCtx = tempCanvas.getContext('2d');
            tempCtx.putImageData(imageData, 0, 0);

            // Apply blur first
            ctx.filter = 'blur(1px)';
            ctx.drawImage(tempCanvas, 0, 0);

            // Then combine for sharpening effect
            ctx.globalCompositeOperation = 'difference';
            ctx.drawImage(tempCanvas, 0, 0);
            ctx.globalCompositeOperation = 'source-over';

            return; // Skip the putImageData since we used drawImage

        case 'grayscale':
            // Convert to grayscale
            for (let i = 0; i < data.length; i += 4) {
                const avg = (data[i] + data[i+1] + data[i+2]) / 3;
                data[i] = avg;     // Red
                data[i+1] = avg;   // Green
                data[i+2] = avg;   // Blue
            }
            break;
    }

    // Update canvas with enhanced image
    ctx.putImageData(imageData, 0, 0);
}

// Reset to original image
function resetEnhancement() {
    if (!canvas || !ctx || !originalImageData) return;

    ctx.putImageData(originalImageData, 0, 0);
}

// Save enhanced image
function saveEnhancement() {
    if (!canvas || !selectedImage) return;

    // Get enhanced image data URL
    const enhancedImageUrl = canvas.toDataURL('image/jpeg');

    // Create form data to send to server
    const formData = new FormData();
    formData.append('enhanced_image', enhancedImageUrl);
    formData.append('original_path', selectedImage.getAttribute('data-path'));

    // Show loading 
    if (window.showLoading) {
        window.showLoading('Saving enhanced image...');
    }

    // Send to server
    fetch('/save-enhanced-image', {
        method: 'POST', 
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (window.hideLoading) {
            window.hideLoading();
        }

        if (data.success) {
            // Update the original image with enhanced version
            selectedImage.src = enhancedImageUrl + '?t=' + new Date().getTime(); // Cache busting
            alert('Image enhanced successfully!');

            // Hide enhancement panel
            const enhancementPanel = document.getElementById('enhancement-panel');
            if (enhancementPanel) {
                enhancementPanel.classList.add('d-none');
            }
        } else {
            alert('Error saving enhanced image: ' + data.error);
        }
    })
    .catch(error => {
        if (window.hideLoading) {
            window.hideLoading();
        }
        alert('Error saving enhanced image: ' + error);
    });
}