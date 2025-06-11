// Component filtering functionality
document.addEventListener('DOMContentLoaded', function() {
    // Select all component filter links
    const componentFilters = document.querySelectorAll('.component-filter');

    // Add click event listeners to each filter
    componentFilters.forEach(filter => {
        filter.addEventListener('click', function(e) {
            e.preventDefault();

            // Get the filter type from data attribute
            const filterType = this.getAttribute('data-filter');

            // Remove active class from all filters
            componentFilters.forEach(f => f.classList.remove('active'));

            // Add active class to clicked filter
            this.classList.add('active');

            // Apply the filtering
            filterComponents(filterType);
        });
    });

    // Function to filter components
    function filterComponents(type) {
        // Get all component items
        const allComponents = document.querySelectorAll('.component-item');

        // Check if we're viewing the results page (has components)
        if (allComponents.length === 0) return;

        // If 'all' is selected or no type specified, show all components
        if (!type || type === 'all') {
            allComponents.forEach(comp => {
                comp.style.display = 'block';
            });
            return;
        }

        // Hide all components first
        allComponents.forEach(comp => {
            comp.style.display = 'none';
        });

        // Show only components matching the filter
        document.querySelectorAll(`.component-item[data-type="${type}"]`).forEach(comp => {
            comp.style.display = 'block';
        });
    }

    // Initialize - check if there's a filter parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const filterParam = urlParams.get('filter');

    if (filterParam) {
        // Find the corresponding filter link
        const activeFilter = document.querySelector(`.component-filter[data-filter="${filterParam}"]`);
        if (activeFilter) {
            // Trigger a click on that filter
            activeFilter.click();
        }
    }
});

// Add component zoom functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get all cropped images
    const croppedImages = document.querySelectorAll('.cropped-img');
    let overlay;

    // Create overlay for fullscreen view if it doesn't exist
    if (!document.querySelector('.fullscreen-overlay')) {
        overlay = document.createElement('div');
        overlay.className = 'fullscreen-overlay';
        document.body.appendChild(overlay);

        // Close fullscreen when clicking on overlay
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeFullscreen();
            }
        });
    } else {
        overlay = document.querySelector('.fullscreen-overlay');
    }

    // Function to close fullscreen view
    function closeFullscreen() {
        const zoomedImg = document.querySelector('.cropped-img.zoomed');
        const zoomedContainer = document.querySelector('.cropped-img-container.zoomed-container');

        if (zoomedImg) zoomedImg.classList.remove('zoomed');
        if (zoomedContainer) zoomedContainer.classList.remove('zoomed-container');
        overlay.classList.remove('active');
    }

    // Add escape key to close fullscreen
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeFullscreen();
        }
    });

    croppedImages.forEach(img => {
        img.addEventListener('click', function(e) {
            e.preventDefault();

            // Toggle zoomed class for CSS transition effect
            this.classList.toggle('zoomed');

            // Get parent container
            const container = this.closest('.cropped-img-container');
            if (container) {
                container.classList.toggle('zoomed-container');

                // Toggle overlay
                if (container.classList.contains('zoomed-container')) {
                    overlay.classList.add('active');
                } else {
                    overlay.classList.remove('active');
                }
            }
        });
    });
});