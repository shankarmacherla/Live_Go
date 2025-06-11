// Component Management functionality
document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAllComponents');
    const componentCheckboxes = document.querySelectorAll('.component-checkbox');
    const bulkActions = document.querySelector('.bulk-actions');
    const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
    const deleteButtons = document.querySelectorAll('.delete-component');

    // Component details modal elements
    const detailsModal = document.getElementById('component-details-modal');
    const closeDetailsBtn = document.getElementById('close-component-details');
    const detailsImage = document.getElementById('component-details-image');
    const detailsTitle = document.getElementById('component-details-title');
    const detailsType = document.getElementById('component-details-type');
    const detailsTypeValue = document.getElementById('component-details-type-value');
    const detailsPath = document.getElementById('component-details-path');
    const detailsSize = document.getElementById('component-details-size');
    const detailsDimensions = document.getElementById('component-details-dimensions');
    const detailsCreated = document.getElementById('component-details-created');
    const detailsDeleteBtn = document.getElementById('component-details-delete');

    // Skip if we're not on the components page
    if (!selectAllCheckbox) return;

    // Function to toggle bulk actions visibility
    function toggleBulkActions() {
        const checkedComponents = document.querySelectorAll('.component-checkbox:checked');
        if (checkedComponents.length > 0) {
            bulkActions.classList.remove('d-none');
        } else {
            bulkActions.classList.add('d-none');
        }
    }

    // Select all components
    selectAllCheckbox.addEventListener('change', function() {
        componentCheckboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        toggleBulkActions();
    });

    // Individual component selection
    componentCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            // Update "select all" checkbox
            if (!this.checked) {
                selectAllCheckbox.checked = false;
            } else {
                // Check if all components are selected
                const allChecked = Array.from(componentCheckboxes).every(cb => cb.checked);
                selectAllCheckbox.checked = allChecked;
            }
            toggleBulkActions();
        });
    });

    // Delete individual component
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const path = this.getAttribute('data-path');
            if (confirm('Are you sure you want to delete this component?')) {
                deleteComponent(path);
            }
        });
    });

    // Delete selected components
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', function() {
            const selectedPaths = [];
            document.querySelectorAll('.component-checkbox:checked').forEach(checkbox => {
                selectedPaths.push(checkbox.getAttribute('data-path'));
            });

            if (selectedPaths.length === 0) {
                alert('No components selected');
                return;
            }

            if (confirm(`Are you sure you want to delete ${selectedPaths.length} selected components?`)) {
                deleteMultipleComponents(selectedPaths);
            }
        });
    }

    // Function to delete a single component
    function deleteComponent(path) {
        // Send delete request to server
        fetch('/delete_component', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ path: path })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove component from UI
                const componentItems = document.querySelectorAll(`.component-item`);
                componentItems.forEach(item => {
                    const checkboxPath = item.querySelector('.component-checkbox').getAttribute('data-path');
                    if (checkboxPath === path) {
                        item.remove();
                    }
                });

                // Show success message
                alert('Component deleted successfully');

                // Refresh page if all components are deleted
                if (document.querySelectorAll('.component-item').length === 0) {
                    window.location.reload();
                }
            } else {
                alert('Error deleting component: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting component');
        });
    }

    // Function to delete multiple components
    function deleteMultipleComponents(paths) {
        // Send delete request to server
        fetch('/delete_components', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ paths: paths })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove components from UI
                paths.forEach(path => {
                    const componentItems = document.querySelectorAll(`.component-item`);
                    componentItems.forEach(item => {
                        const checkboxPath = item.querySelector('.component-checkbox').getAttribute('data-path');
                        if (checkboxPath === path) {
                            item.remove();
                        }
                    });
                });

                // Show success message and refresh
                alert(`${data.deleted_count} components deleted successfully`);
                window.location.reload();
            } else {
                alert('Error deleting components: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting components');
        });
    }

    // Component details modal functionality
    if (detailsModal && closeDetailsBtn) {
        // Show component details
        const croppedImages = document.querySelectorAll('.cropped-img');
        croppedImages.forEach(img => {
            img.addEventListener('dblclick', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const container = this.closest('.cropped-img-container');
                const checkbox = container.querySelector('.component-checkbox');
                const path = checkbox.getAttribute('data-path');
                const type = path.split('/').pop().split('_')[0];

                // Set details in modal
                detailsImage.src = img.src;
                detailsTitle.textContent = `Component: ${type.charAt(0).toUpperCase() + type.slice(1)}`;
                detailsType.textContent = type;
                detailsTypeValue.textContent = type;
                detailsPath.textContent = path;

                // Get additional information
                fetch(`/component_info?path=${encodeURIComponent(path)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        detailsSize.textContent = data.size;
                        detailsDimensions.textContent = data.dimensions;
                        detailsCreated.textContent = data.created;
                    }
                })
                .catch(error => {
                    console.error('Error fetching component details:', error);
                });

                // Set delete button path
                detailsDeleteBtn.setAttribute('data-path', path);

                // Show modal
                detailsModal.classList.add('active');
            });
        });

        // Close modal
        closeDetailsBtn.addEventListener('click', function() {
            detailsModal.classList.remove('active');
        });

        // Close modal on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && detailsModal.classList.contains('active')) {
                detailsModal.classList.remove('active');
            }
        });

        // Close modal when clicking outside
        detailsModal.addEventListener('click', function(e) {
            if (e.target === detailsModal) {
                detailsModal.classList.remove('active');
            }
        });

        // Delete button in details modal
        detailsDeleteBtn.addEventListener('click', function() {
            const path = this.getAttribute('data-path');
            if (confirm('Are you sure you want to delete this component?')) {
                deleteComponent(path);
                detailsModal.classList.remove('active');
            }
        });
    }
});