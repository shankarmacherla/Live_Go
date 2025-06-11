// DOM Elements
const uploadForm = document.getElementById('upload-form');
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadPreview = document.getElementById('upload-preview');
const loadingContainer = document.getElementById('loading-container');
const errorMessage = document.getElementById('error-message');

// Initialize the file upload functionality
function initializeUpload() {
    if (!uploadArea || !fileInput) return;

    // Click on upload area triggers file input
    uploadArea.addEventListener('click', (e) => {
        if (e.target === uploadArea || !e.target.closest('img')) {
            fileInput.click();
        }
    });

    // File input change handler
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop event handlers
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    }
}

// Handle file selection from input
function handleFileSelect() {
    if (fileInput.files.length) {
        displayFilePreview(fileInput.files[0]);
    }
}

// Handle drag over event
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

// Handle drag leave event
function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

// Handle drop event
function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        displayFilePreview(e.dataTransfer.files[0]);
    }
}

// Display file preview
function displayFilePreview(file) {
    if (!file.type.match('image.*')) {
        showError('Please select an image file (JPEG, PNG, etc.)');
        return;
    }

    hideError();

    // Use the enhanced shared function for file preview
    enhancedDisplayFilePreview(
        file, 
        uploadPreview, 
        uploadArea, 
        document.getElementById('file-name-display')
    );

    // Don't show success message yet - wait for the button click
}

// Handle form submission
function handleFormSubmit(e) {
    if (!fileInput.files.length) {
        e.preventDefault();
        showError('Please select an image to upload');
        return;
    }

    // Prevent the form from actually submitting and reloading the page
    e.preventDefault();

    // First, upload the image
    const formData = new FormData(uploadForm);

    // Save the file to the server without redirection
    fetch('/detect', {
        method: 'POST',
        body: formData
    }).then(response => {
        console.log('Image uploaded and segmented_outputs cleaned');
    }).catch(error => {
        console.error('Error:', error);
    });

    // Show success message
    const successMessage = document.getElementById('success-message');
    if (successMessage) {
        successMessage.style.display = 'block';

        // Scroll to success message if needed
        successMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Keep the message visible longer (5 seconds)
        setTimeout(function() {
            successMessage.style.display = 'none';
        }, 5000);
    }
}

// Show error message
function showError(message) {
    if (errorMessage) {
        errorMessage.textContent = message;
        errorMessage.classList.add('show');
    }
}

// Hide error message
function hideError() {
    if (errorMessage) {
        errorMessage.classList.remove('show');
    }
}

// Show loading indicator
function showLoading(message) {
    if (loadingContainer) {
        const loadingText = document.getElementById('loading-text');
        if (loadingText) {
            loadingText.textContent = message || 'Processing...';
        }
        loadingContainer.style.display = 'flex';
    }
}

// Hide loading indicator
function hideLoading() {
    if (loadingContainer) {
        loadingContainer.style.display = 'none';
    }
}

// Initialize image comparison gallery in results page
function initializeResultsGallery() {
    const croppedImages = document.querySelectorAll('.cropped-img');

    croppedImages.forEach(img => {
        img.addEventListener('click', function() {
            // Could expand this to show full-size image in a modal
            // For now, just add a simple zoom effect
            this.classList.toggle('zoomed');
        });
    });
}

// Sidebar toggle functionality
function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');

    // Check for saved sidebar state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';

    if (sidebarCollapsed) {
        sidebar.classList.add('collapsed');
        sidebarToggle.classList.add('collapsed');
        mainContent.classList.add('full-width');
    }

    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
        sidebarToggle.classList.toggle('collapsed');
        mainContent.classList.toggle('full-width');

        // Save sidebar state in localStorage
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));

        // Prevent the main content from moving when sidebar is toggled
        document.body.style.overflow = 'hidden'; // Temporarily disable scrolling
        setTimeout(() => {
            document.body.style.overflow = ''; // Re-enable scrolling after transition
        }, 300); // Match the transition time in CSS
    });

    // For small screens, collapse sidebar by default
    if (window.innerWidth < 992) {
        sidebar.classList.add('collapsed');
        sidebarToggle.classList.add('collapsed');
        mainContent.classList.add('full-width');
    }
}

// Show success message
function showSuccessMessage() {
    const successMessage = document.getElementById('success-message');
    if (successMessage) {
        successMessage.style.display = 'block';

        // Hide success message after 3 seconds
        setTimeout(function() {
            successMessage.style.display = 'none';
        }, 3000);
    }
}

// Initialize camera functionality
function initializeCamera() {
    console.log("Initializing camera functionality");

    // Check if camera elements exist
    const cameraButton = document.getElementById('camera-button');
    const cameraSection = document.getElementById('camera-section');
    if (!cameraButton) {
        console.log("Camera button not found");
        return;
    }
    if (!cameraSection) {
        console.error("Camera section not found");
        return;
    }

    // Create references to camera elements
    let cameraView, cameraCanvas, cameraOutput, captureButton, useCaptureButton, retakeButton, flipCameraButton, closeButton;
    let stream = null;
    let facingMode = 'environment'; // Start with rear camera by default
    let cameraInitialized = false;

    // Camera button shows the camera section
    cameraButton.addEventListener('click', function(e) {
        e.preventDefault();
        console.log("Camera button clicked");

        // Initialize elements now (to ensure they exist in the DOM)
        cameraView = document.getElementById('camera-view');
        cameraCanvas = document.getElementById('camera-canvas');
        cameraOutput = document.getElementById('camera-output');
        captureButton = document.getElementById('capture-button');
        useCaptureButton = document.getElementById('use-capture-button');
        retakeButton = document.getElementById('retake-button');
        flipCameraButton = document.getElementById('flip-camera');
        closeButton = document.getElementById('close-camera');

        // Show the camera section
        cameraSection.style.display = 'block';

        // Reset camera output
        cameraOutput.style.display = 'none';
        cameraOutput.src = '';

        // Hide upload prompt
        const uploadPrompt = document.getElementById('upload-prompt');
        if (uploadPrompt) {
            uploadPrompt.style.display = 'none';
        }

        // Show capture help text
        const captureHelpText = document.querySelector('.capture-help-text');
        if (captureHelpText) {
            captureHelpText.style.display = 'block';
        }

        // Reset buttons
        if (captureButton) captureButton.style.display = 'inline-block';
        if (useCaptureButton) useCaptureButton.style.display = 'none';
        if (retakeButton) retakeButton.style.display = 'none';

        // Scroll to camera section
        cameraSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Start the camera with a short delay
        setTimeout(function() {
            startCamera();
        }, 300);
    });

    // Initialize the camera button handlers if not already done
    if (!cameraInitialized) {
        // We'll set this to true when camera is first shown

        // Setup the button handlers
        setUpCameraButtonHandlers();
    }

    function setUpCameraButtonHandlers() {
        console.log("Setting up camera button handlers");

        // Capture button
        document.getElementById('capture-button').addEventListener('click', function() {
            console.log("Capture button clicked");
            takePicture();
        });

        // Use captured image button
        document.getElementById('use-capture-button').addEventListener('click', function() {
            console.log("Use capture button clicked");
            useCapturedImage();
        });

        // Retake photo button
        document.getElementById('retake-button').addEventListener('click', function() {
            console.log("Retake button clicked");
            retakePhoto();
        });

        // Flip camera button
        document.getElementById('flip-camera').addEventListener('click', function() {
            console.log("Flip camera button clicked");
            facingMode = facingMode === 'user' ? 'environment' : 'user';
            stopCamera();
            startCamera();
        });

        // Close camera button
        document.getElementById('close-camera').addEventListener('click', function() {
            console.log("Close camera button clicked");
            cameraSection.style.display = 'none';
            stopCamera();
        });

        // Mark as initialized
        cameraInitialized = true;
    }

    function useCapturedImage() {
        if (!cameraOutput || !cameraOutput.src) {
            console.error("No captured image available");
            return;
        }

        const dataUrl = cameraOutput.src;

        // Generate a filename with timestamp
        const filename = `camera_capture_${new Date().getTime()}.jpg`;

        console.log("Using captured image:", filename);

        // Store the image data for sharing with other pages
        saveUploadedImage(dataUrl, filename);

        // Display the image in the upload area
        const uploadPreview = document.getElementById('upload-preview');
        const uploadArea = document.getElementById('upload-area');
        const fileNameDisplay = document.getElementById('file-name-display');

        if (uploadPreview && uploadArea) {
            // Apply a transition effect
            uploadArea.classList.add('highlight-transition');

            // Update the preview
            uploadPreview.src = dataUrl;
            uploadPreview.style.display = 'block';
            uploadArea.classList.add('has-preview');

            if (fileNameDisplay) {
                fileNameDisplay.textContent = filename;
            }

            // Scroll to the upload area
            setTimeout(() => {
                uploadArea.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Add and then remove a highlight effect
                setTimeout(() => {
                    uploadArea.classList.add('highlight-effect');
                    setTimeout(() => {
                        uploadArea.classList.remove('highlight-effect');
                        uploadArea.classList.remove('highlight-transition');
                    }, 1500);
                }, 300);
            }, 100);
        }

        // Show success message with camera-specific text
        const successMessage = document.getElementById('success-message');
        if (successMessage) {
            successMessage.innerHTML = '<i class="bi bi-camera-fill me-2"></i>Image captured and ready for upload!';
            successMessage.style.display = 'block';

            // Hide success message after 3 seconds
            setTimeout(function() {
                successMessage.style.display = 'none';
            }, 3000);
        }

        // Hide the camera section
        cameraSection.style.display = 'none';
        stopCamera();
    }

    function retakePhoto() {
        if (!cameraOutput) return;

        console.log("Retaking photo");
        cameraOutput.style.display = 'none';

        // Hide upload prompt
        const uploadPrompt = document.getElementById('upload-prompt');
        if (uploadPrompt) {
            uploadPrompt.style.display = 'none';
        }

        // Show the capture help text again
        const captureHelpText = document.querySelector('.capture-help-text');
        if (captureHelpText) captureHelpText.style.display = 'block';

        // Check if we're using the simulated camera
        const simulatedView = document.getElementById('simulated-camera-view');
        if (simulatedView) {
            console.log("Showing simulated camera view again");
            simulatedView.style.display = 'flex';
        } else if (cameraView) {
            // Real camera
            cameraView.style.display = 'block';
        }

        // Reset button states
        if (captureButton) {
            captureButton.style.display = 'inline-block';
            captureButton.classList.add('pulse-animation');
        }
        if (useCaptureButton) {
            useCaptureButton.style.display = 'none';
            useCaptureButton.classList.remove('pulse-animation');
        }
        if (retakeButton) retakeButton.style.display = 'none';
    }

    function startCamera() {
        if (!cameraView) {
            console.error("Camera view element not found");
            return;
        }

        console.log("Starting camera with facing mode:", facingMode);

        // Reset UI state
        cameraOutput.style.display = 'none';
        cameraView.style.display = 'block';

        if (captureButton) captureButton.style.display = 'inline-block';
        if (useCaptureButton) useCaptureButton.style.display = 'none';
        if (retakeButton) retakeButton.style.display = 'none';

        // Check if we're in a demo/simulation environment
        const isSimulated = window.location.hostname.includes('replit') || 
                           !navigator.mediaDevices || 
                           !navigator.mediaDevices.getUserMedia;

        if (isSimulated) {
            console.log("Using simulated camera in demo environment");

            // Show a custom background for the simulated camera
            cameraView.style.display = 'none';

            // Create a simulated camera view (using a canvas)
            const simulatedView = document.createElement('div');
            simulatedView.id = 'simulated-camera-view';
            simulatedView.style.width = '100%';
            simulatedView.style.height = '300px';
            simulatedView.style.backgroundColor = '#333';
            simulatedView.style.display = 'flex';
            simulatedView.style.alignItems = 'center';
            simulatedView.style.justifyContent = 'center';
            simulatedView.style.borderRadius = '8px';
            simulatedView.style.color = '#fff';
            simulatedView.style.flexDirection = 'column';
            simulatedView.style.position = 'relative';

            // Add an icon
            const cameraIcon = document.createElement('div');
            cameraIcon.innerHTML = '<i class="bi bi-camera" style="font-size: 64px; opacity: 0.5;"></i>';
            simulatedView.appendChild(cameraIcon);

            // Add simulated view text
            const simulatedText = document.createElement('div');
            simulatedText.textContent = 'Simulated Camera (Demo Mode)';
            simulatedText.style.marginTop = '1rem';
            simulatedText.style.opacity = '0.7';
            simulatedView.appendChild(simulatedText);

            // Add capture instruction
            const captureInstruction = document.createElement('div');
            captureInstruction.textContent = 'Click "Capture" to take a simulated photo';
            captureInstruction.style.marginTop = '0.5rem';
            captureInstruction.style.fontSize = '0.9em';
            captureInstruction.style.opacity = '0.5';
            simulatedView.appendChild(captureInstruction);

            // Insert the simulated view before the camera view
            cameraView.parentNode.insertBefore(simulatedView, cameraView);

            return; // Skip actual camera initialization
        }

        // Regular camera implementation for supported browsers
        // Check if browser supports getUserMedia
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error("Browser doesn't support getUserMedia");

            const cameraErrorEl = document.getElementById('camera-error');
            const cameraErrorMessageEl = document.getElementById('camera-error-message');

            if (cameraErrorEl && cameraErrorMessageEl) {
                cameraErrorMessageEl.textContent = "Your browser doesn't support camera access. Please try a different browser or use the file upload option.";
                cameraErrorEl.style.display = 'block';
            } else {
                alert("Your browser doesn't support camera access. Please try a different browser or use the file upload option.");
            }

            // Don't hide the modal, let the user close it
            return;
        }

        // Get camera stream with additional constraints for mobile
        const constraints = {
            video: {
                facingMode: facingMode,
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        };

        console.log("Requesting media with constraints:", constraints);

        navigator.mediaDevices.getUserMedia(constraints)
            .then(function(videoStream) {
                console.log("Camera stream obtained successfully");
                stream = videoStream;
                cameraView.srcObject = stream;

                // Play the video element
                cameraView.play().catch(error => {
                    console.error("Error playing video:", error);
                });
            })
            .catch(function(error) {
                console.error("Camera error:", error);

                const cameraErrorEl = document.getElementById('camera-error');
                const cameraErrorMessageEl = document.getElementById('camera-error-message');

                if (cameraErrorEl && cameraErrorMessageEl) {
                    cameraErrorMessageEl.textContent = "Error accessing camera: " + error.message + ". Please ensure you've granted camera permissions.";
                    cameraErrorEl.style.display = 'block';
                } else {
                    alert("Error accessing camera: " + error.message + ". Please ensure you've granted camera permissions or try another browser.");
                }
            });
    }

    function stopCamera() {
        console.log("Stopping camera");
        if (stream) {
            stream.getTracks().forEach(track => {
                track.stop();
            });
            stream = null;
        }
    }

    function takePicture() {
        if (!cameraCanvas || !cameraOutput) {
            console.error("Required elements for taking picture not found");
            return;
        }

        console.log("Taking picture");

        // Add a flash effect
        const flashEffect = document.createElement('div');
        flashEffect.style.position = 'fixed';
        flashEffect.style.top = '0';
        flashEffect.style.left = '0';
        flashEffect.style.width = '100%';
        flashEffect.style.height = '100%';
        flashEffect.style.backgroundColor = 'white';
        flashEffect.style.opacity = '0.8';
        flashEffect.style.zIndex = '9999';
        flashEffect.style.pointerEvents = 'none';
        document.body.appendChild(flashEffect);

        // Remove flash effect after a short time
        setTimeout(() => {
            flashEffect.style.opacity = '0';
            flashEffect.style.transition = 'opacity 0.3s ease-out';
            setTimeout(() => {
                document.body.removeChild(flashEffect);
            }, 300);
        }, 100);

        // Check if we're using the simulated camera
        const simulatedView = document.getElementById('simulated-camera-view');
        const isSimulated = simulatedView && simulatedView.style.display !== 'none';

        if (isSimulated) {
            console.log("Taking simulated picture");

            // Setup canvas for simulated picture
            const width = 1280;
            const height = 720;
            cameraCanvas.width = width;
            cameraCanvas.height = height;

            // Generate a "simulated" image with some demo content
            const context = cameraCanvas.getContext('2d');

            // Fill background
            context.fillStyle = '#333';
            context.fillRect(0, 0, width, height);

            // Draw some network component shapes for the demo
            // Draw a switch
            context.fillStyle = '#1a73e8';
            context.fillRect(width/2 - 150, height/2 - 50, 300, 100);

            // Draw some ports
            context.fillStyle = '#e8e8e8';
            for (let i = 0; i < 8; i++) {
                context.fillRect(width/2 - 140 + i*40, height/2 + 30, 30, 10);
            }

            // Draw a rack structure
            context.strokeStyle = '#999';
            context.lineWidth = 5;
            context.strokeRect(width/2 - 200, height/2 - 150, 400, 300);

            // Add some text
            context.fillStyle = '#fff';
            context.font = 'bold 24px Arial';
            context.textAlign = 'center';
            context.fillText('Simulated Network Component', width/2, height/2 - 70);

            // Convert to data URL
            try {
                const dataUrl = cameraCanvas.toDataURL('image/jpeg');

                // Show the captured image
                cameraOutput.src = dataUrl;
                cameraOutput.style.display = 'block';

                // Hide the simulated view
                simulatedView.style.display = 'none';

                // Show upload prompt
                const uploadPrompt = document.getElementById('upload-prompt');
                if (uploadPrompt) {
                    uploadPrompt.style.display = 'block';
                }

                // Update buttons
                if (captureButton) captureButton.style.display = 'none';
                if (useCaptureButton) {
                    useCaptureButton.style.display = 'inline-block';
                    useCaptureButton.classList.add('pulse-animation');
                }
                if (retakeButton) retakeButton.style.display = 'inline-block';

                // Hide the capture help text
                const captureHelpText = document.querySelector('.capture-help-text');
                if (captureHelpText) captureHelpText.style.display = 'none';
            } catch (err) {
                console.error("Error creating simulated image:", err);
                alert("Error creating simulated image. Please try again.");
            }
        } else {
            // Using real camera
            // Set canvas dimensions to match video
            const width = cameraView.videoWidth;
            const height = cameraView.videoHeight;

            if (width === 0 || height === 0) {
                console.error("Video has zero width or height, can't capture");
                alert("Camera not ready yet. Please try again in a moment.");
                return;
            }

            console.log("Video dimensions:", width, height);
            cameraCanvas.width = width;
            cameraCanvas.height = height;

            // Draw video frame to canvas and convert to image
            const context = cameraCanvas.getContext('2d');
            context.drawImage(cameraView, 0, 0, width, height);

            try {
                const dataUrl = cameraCanvas.toDataURL('image/jpeg');

                // Show the captured image
                cameraOutput.src = dataUrl;
                cameraOutput.style.display = 'block';
                cameraView.style.display = 'none';

                // Show upload prompt
                const uploadPrompt = document.getElementById('upload-prompt');
                if (uploadPrompt) {
                    uploadPrompt.style.display = 'block';
                }

                // Update buttons
                if (captureButton) captureButton.style.display = 'none';
                if (useCaptureButton) {
                    useCaptureButton.style.display = 'inline-block';
                    useCaptureButton.classList.add('pulse-animation');
                }
                if (retakeButton) retakeButton.style.display = 'inline-block';

                // Hide the capture help text
                const captureHelpText = document.querySelector('.capture-help-text');
                if (captureHelpText) captureHelpText.style.display = 'none';
            } catch (err) {
                console.error("Error creating data URL:", err);
                alert("Error capturing image. Please try again.");
            }
        }
    }
}

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    initializeUpload();
    initializeSidebar();

    // Initialize camera if we're on the homepage
    if (document.getElementById('camera-button')) {
        initializeCamera();
    }

    // Apply last uploaded image if available (for cross-page image sharing)
    applyLastUploadedImage();

    // Check if we're on results page
    if (document.querySelector('.result-gallery')) {
        initializeResultsGallery();
    }

    // Hide loading indicator on page load (in case it was left visible)
    hideLoading();

    // Set active sidebar links based on current URL
    const currentUrl = window.location.href;
    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
        if (currentUrl.includes(link.getAttribute('href'))) {
            link.classList.add('active');
        }
    });

    // Handle filter from URL
    const urlParams = new URLSearchParams(window.location.search);
    const filter = urlParams.get('filter');
    if (filter) {
        document.querySelectorAll('.component-filter').forEach(link => {
            if (link.getAttribute('data-filter') === filter) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
});
