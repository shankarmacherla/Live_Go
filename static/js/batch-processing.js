/**
 * Batch Processing Module
 * Provides functionality for uploading and processing multiple images at once
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const dropArea = document.getElementById('batch-drop-area');
    const fileInput = document.getElementById('batch-file-input');
    const fileList = document.getElementById('file-list');
    const fileItemsContainer = document.getElementById('file-items-container');
    const clearFilesBtn = document.getElementById('clear-files');
    const processBatchBtn = document.getElementById('process-batch');
    const batchesContainer = document.getElementById('batches-container');
    const batchesList = document.getElementById('batches-list');
    const noBatchesMessage = document.getElementById('no-batches-message');

    // Templates
    const batchTemplate = document.getElementById('batch-template');
    const imageTemplate = document.getElementById('image-template');

    // Selected files for batch processing
    let selectedFiles = [];

    // Status refresh interval
    let statusInterval = null;

    // Initialize the batch processing page
    function initBatchProcessing() {
        // Setup event listeners
        setupDropArea();
        setupButtons();

        // Load existing batches
        loadBatches();

        // Set up status refresh interval
        statusInterval = setInterval(refreshBatchesStatus, 5000);
    }

    // Setup drag and drop area
    function setupDropArea() {
        // Click to select files
        dropArea.addEventListener('click', function() {
            fileInput.click();
        });

        // File selection change
        fileInput.addEventListener('change', function() {
            handleFilesSelected(fileInput.files);
        });

        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight drop area when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight() {
            dropArea.classList.add('dragover');
        }

        function unhighlight() {
            dropArea.classList.remove('dragover');
        }

        // Handle dropped files
        dropArea.addEventListener('drop', function(e) {
            const files = e.dataTransfer.files;
            handleFilesSelected(files);
        });
    }

    // Setup buttons
    function setupButtons() {
        // Clear files button
        clearFilesBtn.addEventListener('click', function() {
            clearSelectedFiles();
        });

        // Process batch button
        processBatchBtn.addEventListener('click', function() {
            processBatch();
        });
    }

    // Handle selected files
    function handleFilesSelected(fileList) {
        // Filter only image files
        const imageFiles = Array.from(fileList).filter(file => {
            return file.type.startsWith('image/');
        });

        if (imageFiles.length === 0) {
            showError('Please select valid image files.');
            return;
        }

        // Add to selected files
        imageFiles.forEach(file => {
            // Check if file already exists in the list
            const exists = selectedFiles.some(f => 
                f.name === file.name && 
                f.size === file.size && 
                f.lastModified === file.lastModified
            );

            if (!exists) {
                selectedFiles.push(file);
            }
        });

        updateFileList();
    }

    // Update the file list display
    function updateFileList() {
        // Show file list if there are files
        if (selectedFiles.length > 0) {
            fileList.classList.remove('d-none');
            processBatchBtn.disabled = false;
        } else {
            fileList.classList.add('d-none');
            processBatchBtn.disabled = true;
        }

        // Clear existing items
        fileItemsContainer.innerHTML = '';

        // Add items for each file
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';

            // Create image preview
            const reader = new FileReader();
            reader.onload = function(e) {
                // Create thumbnail
                const thumbnail = document.createElement('img');
                thumbnail.src = e.target.result;
                thumbnail.className = 'image-preview-thumbnail';
                fileItem.prepend(thumbnail);
            };
            reader.readAsDataURL(file);

            // Create file info
            fileItem.innerHTML += `
                <div class="file-icon">
                    <i class="bi bi-file-earmark-image"></i>
                </div>
                <div class="file-name">${file.name}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
                <div class="remove-file" data-index="${index}">
                    <i class="bi bi-x-circle"></i>
                </div>
            `;

            fileItemsContainer.appendChild(fileItem);

            // Add remove file event listener
            fileItem.querySelector('.remove-file').addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                selectedFiles.splice(index, 1);
                updateFileList();
            });
        });
    }

    // Clear all selected files
    function clearSelectedFiles() {
        selectedFiles = [];
        updateFileList();
    }

    // Process the batch
    function processBatch() {
        if (selectedFiles.length === 0) {
            showError('Please select at least one image to process.');
            return;
        }

        showLoading('Uploading batch images...');

        // Create FormData to send files
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('images', file);
        });

        // Send files to server
        fetch('/create_batch', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();

            if (data.success) {
                // Clear selected files
                clearSelectedFiles();

                // Show success message
                showSuccessMessage('Batch processing started successfully.');

                // Add batch to the list
                addBatchToList(data.batch_id);

                // Refresh batch status
                refreshBatchesStatus();
            } else {
                showError(data.error || 'Error creating batch.');
            }
        })
        .catch(error => {
            hideLoading();
            showError('Error uploading files: ' + error.message);
        });
    }

    // Load existing batches
    function loadBatches() {
        fetch('/get_all_batches')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const batches = data.batches;

                // Show/hide no batches message
                if (Object.keys(batches).length === 0) {
                    noBatchesMessage.style.display = 'block';
                } else {
                    noBatchesMessage.style.display = 'none';

                    // Clear existing batches
                    batchesList.innerHTML = '';

                    // Add each batch
                    Object.keys(batches).forEach(batchId => {
                        renderBatch(batches[batchId]);
                    });
                }
            } else {
                console.error('Error loading batches:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading batches:', error);
        });
    }

    // Add a new batch to the list
    function addBatchToList(batchId) {
        fetch(`/get_batch_status/${batchId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Hide no batches message
                noBatchesMessage.style.display = 'none';

                // Render the batch
                renderBatch(data.batch);
            } else {
                console.error('Error getting batch status:', data.error);
            }
        })
        .catch(error => {
            console.error('Error getting batch status:', error);
        });
    }

    // Render a batch in the UI
    function renderBatch(batch) {
        // Check if batch already exists in the list
        let batchElement = document.querySelector(`.batch-card[data-batch-id="${batch.id}"]`);

        if (!batchElement) {
            // Create new batch element
            const template = batchTemplate.content.cloneNode(true);
            batchElement = template.querySelector('.batch-card');
            batchElement.setAttribute('data-batch-id', batch.id);

            // Add to list (newest first)
            if (batchesList.firstChild) {
                batchesList.insertBefore(batchElement, batchesList.firstChild);
            } else {
                batchesList.appendChild(batchElement);
            }

            // Setup batch details toggle
            const detailsToggle = batchElement.querySelector('.batch-details-toggle');
            const detailsSection = batchElement.querySelector('.batch-details');

            detailsToggle.addEventListener('click', function() {
                detailsSection.classList.toggle('expanded');

                const toggleIcon = this.querySelector('i');
                const toggleText = this.querySelector('span');

                if (detailsSection.classList.contains('expanded')) {
                    toggleIcon.classList.replace('bi-chevron-down', 'bi-chevron-up');
                    toggleText.textContent = 'Hide Details';
                } else {
                    toggleIcon.classList.replace('bi-chevron-up', 'bi-chevron-down');
                    toggleText.textContent = 'Show Details';
                }
            });
        }

        // Update batch information
        updateBatchElement(batchElement, batch);
    }

    // Update batch element with latest information
    function updateBatchElement(element, batch) {
        // Update basic information
        element.querySelector('.batch-id').textContent = batch.id;
        element.querySelector('.image-count').textContent = batch.images.length;

        // Format timestamps
        if (batch.start_time) {
            element.querySelector('.start-time').textContent = formatDateTime(batch.start_time * 1000);
        } else {
            element.querySelector('.start-time').textContent = 'Pending';
        }

        // Update status badge
        const statusBadge = element.querySelector('.batch-status-badge');
        statusBadge.textContent = capitalizeFirst(batch.status);

        // Style based on status
        statusBadge.className = 'batch-status-badge';
        if (batch.status === 'pending') {
            statusBadge.classList.add('bg-warning', 'text-dark');
        } else if (batch.status === 'processing') {
            statusBadge.classList.add('bg-info', 'text-white');
        } else if (batch.status === 'completed') {
            statusBadge.classList.add('bg-success', 'text-white');
        } else if (batch.status === 'failed') {
            statusBadge.classList.add('bg-danger', 'text-white');
        } else if (batch.status === 'partial') {
            statusBadge.classList.add('bg-warning', 'text-white');
        }

        // Update progress
        const progressBar = element.querySelector('.progress-bar');
        const progressPercentage = element.querySelector('.progress-percentage');

        progressBar.style.width = `${batch.progress}%`;
        progressPercentage.textContent = `${batch.progress}%`;

        // Style progress bar with blue and white theme
        progressBar.className = 'progress-bar progress-bar-striped';
        progressBar.style.background = 'linear-gradient(45deg, #0052cc, #4195ff, #66b3ff)';
        progressBar.style.boxShadow = '0 2px 12px rgba(0, 82, 204, 0.4), inset 0 1px 2px rgba(255,255,255,0.3)';
        progressBar.style.borderRadius = '8px';
        
        if (batch.status === 'processing') {
            progressBar.classList.add('progress-bar-animated');
            progressBar.style.background = 'linear-gradient(45deg, #0052cc, #4195ff, #66b3ff)';
        } else if (batch.status === 'completed') {
            progressBar.style.background = 'linear-gradient(45deg, #0052cc, #4195ff, #66b3ff)';
            progressBar.style.boxShadow = '0 4px 20px rgba(0, 82, 204, 0.5), inset 0 1px 2px rgba(255,255,255,0.4)';
        } else if (batch.status === 'failed') {
            progressBar.style.background = 'linear-gradient(45deg, #dc3545, #e57373)';
            progressBar.style.boxShadow = '0 2px 12px rgba(220, 53, 69, 0.4)';
        } else if (batch.status === 'partial') {
            progressBar.style.background = 'linear-gradient(45deg, #ffc107, #ffeb3b)';
            progressBar.style.boxShadow = '0 2px 12px rgba(255, 193, 7, 0.4)';
        } else {
            progressBar.style.background = 'linear-gradient(45deg, #6c757d, #adb5bd)';
            progressBar.style.boxShadow = '0 2px 8px rgba(108, 117, 125, 0.3)';
        }

        // Update elapsed time
        const elapsedTimeElement = element.querySelector('.elapsed-time');
        if (batch.start_time) {
            const endTime = batch.end_time || (Date.now() / 1000);
            const elapsedSeconds = endTime - batch.start_time;
            elapsedTimeElement.textContent = formatElapsedTime(elapsedSeconds);
        } else {
            elapsedTimeElement.textContent = 'Waiting...';
        }

        // Show/hide view results button
        const viewResultsBtn = element.querySelector('.view-results-btn');
        if (batch.status === 'completed' || batch.status === 'partial') {
            viewResultsBtn.style.display = 'block';
            viewResultsBtn.onclick = function() {
                window.location.href = `/batch_results/${batch.id}`;
            };
        } else {
            viewResultsBtn.style.display = 'none';
        }

        // Update image list
        const imageList = element.querySelector('.image-list');
        imageList.innerHTML = '';

        batch.images.forEach((image, index) => {
            // Create image element
            const template = imageTemplate.content.cloneNode(true);
            const imageItem = template.querySelector('.image-item');

            imageItem.setAttribute('data-image-index', index);

            // Update image information
            const filenameParts = image.filename.split('/');
            const displayName = filenameParts[filenameParts.length - 1];

            imageItem.querySelector('.filename').textContent = displayName;

            // Set image preview if possible
            const thumbnailImg = imageItem.querySelector('.image-preview-thumbnail');
            thumbnailImg.src = `/static/batch_results/${batch.id}/${displayName}`;
            thumbnailImg.alt = displayName;

            // Update status badge
            const statusBadge = imageItem.querySelector('.image-status');
            statusBadge.textContent = capitalizeFirst(image.status);

            // Style based on status
            statusBadge.className = 'image-status';
            if (image.status === 'pending') {
                statusBadge.classList.add('bg-warning', 'text-dark');
            } else if (image.status === 'processing') {
                statusBadge.classList.add('bg-info', 'text-white');
            } else if (image.status === 'completed') {
                statusBadge.classList.add('bg-success', 'text-white');
            } else if (image.status === 'failed') {
                statusBadge.classList.add('bg-danger', 'text-white');
            }

            // Update processing time
            const processingTimeElement = imageItem.querySelector('.processing-time');
            if (image.start_time && image.end_time) {
                const processingTime = image.end_time - image.start_time;
                processingTimeElement.textContent = `Processing time: ${formatElapsedTime(processingTime)}`;
            } else if (image.start_time) {
                const processingTime = (Date.now() / 1000) - image.start_time;
                processingTimeElement.textContent = `Processing for: ${formatElapsedTime(processingTime)}`;
            } else {
                processingTimeElement.textContent = 'Waiting in queue...';
            }

            // Show/hide actions
            const imageActions = imageItem.querySelector('.image-actions');
            if (image.status === 'completed') {
                imageActions.style.display = 'block';

                // Setup action buttons
                const viewImageBtn = imageItem.querySelector('.view-image-btn');
                const viewCsvBtn = imageItem.querySelector('.view-csv-btn');

                viewImageBtn.href = `/batch_components/${batch.id}/${index}`;
                viewCsvBtn.href = `/batch_results_csv/${batch.id}/${index}`;
            }

            imageList.appendChild(imageItem);
        });
    }

    // Refresh all batches status
    function refreshBatchesStatus() {
        fetch('/get_all_batches')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const batches = data.batches;

                // Update each batch in the UI
                Object.keys(batches).forEach(batchId => {
                    const batchElement = document.querySelector(`.batch-card[data-batch-id="${batchId}"]`);
                    if (batchElement) {
                        updateBatchElement(batchElement, batches[batchId]);
                    } else {
                        renderBatch(batches[batchId]);
                    }
                });

                // Show/hide no batches message
                if (Object.keys(batches).length === 0) {
                    noBatchesMessage.style.display = 'block';
                } else {
                    noBatchesMessage.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Error refreshing batch status:', error);
        });
    }

    // Helper functions

    // Format file size
    function formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' B';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + ' KB';
        } else {
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
    }

    // Format date and time
    function formatDateTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }

    // Format elapsed time
    function formatElapsedTime(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const secs = Math.round(seconds % 60);
            return `${minutes}m ${secs}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    // Capitalize first letter
    function capitalizeFirst(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    // Show error message
    function showError(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'alert alert-danger alert-dismissible fade show mt-3';
        errorElement.innerHTML = `
            <strong><i class="bi bi-exclamation-triangle me-2"></i>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Add to page
        const container = document.querySelector('.container');
        container.insertBefore(errorElement, container.firstChild);

        // Auto dismiss after 5 seconds
        setTimeout(() => {
            errorElement.remove();
        }, 5000);
    }

    // Show success message
    function showSuccessMessage(message) {
        const successElement = document.createElement('div');
        successElement.className = 'alert alert-success alert-dismissible fade show mt-3';
        successElement.innerHTML = `
            <strong><i class="bi bi-check-circle me-2"></i>Success:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Add to page
        const container = document.querySelector('.container');
        container.insertBefore(successElement, container.firstChild);

        // Auto dismiss after 5 seconds
        setTimeout(() => {
            successElement.remove();
        }, 5000);
    }

    // Show loading indicator
    function showLoading(message) {
        const loadingContainer = document.getElementById('loading-container');
        const loadingText = document.getElementById('loading-text');

        loadingText.textContent = message || 'Processing...';
        loadingContainer.style.display = 'flex';
    }

    // Hide loading indicator
    function hideLoading() {
        const loadingContainer = document.getElementById('loading-container');
        loadingContainer.style.display = 'none';
    }

    // Initialize
    initBatchProcessing();

    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (statusInterval) {
            clearInterval(statusInterval);
        }
    });
});