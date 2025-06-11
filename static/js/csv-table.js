// CSV Table enhancement functionality
document.addEventListener('DOMContentLoaded', function() {
    const csvTable = document.getElementById('csv-table');
    const searchInput = document.getElementById('csv-search');
    const rowCount = document.getElementById('row-count');
    const expandBtn = document.getElementById('expand-table');

    // If we're not on the CSV results page, exit
    if (!csvTable) return;

    // Count and display number of rows
    const tbody = csvTable.querySelector('tbody');
    const rows = tbody ? tbody.querySelectorAll('tr') : [];

    if (rowCount) {
        rowCount.textContent = rows.length;
    }

    // Search functionality
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            let visibleRows = 0;

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const display = text.includes(searchTerm) ? '' : 'none';
                row.style.display = display;

                if (display === '') {
                    visibleRows++;
                }
            });

            // Update count of visible rows
            if (rowCount) {
                rowCount.textContent = visibleRows;
            }
        });
    }

    // Fullscreen functionality
    if (expandBtn) {
        expandBtn.addEventListener('click', function() {
            // Create fullscreen container
            const fullscreenContainer = document.createElement('div');
            fullscreenContainer.className = 'table-fullscreen';

            // Create controls for fullscreen mode
            const controls = document.createElement('div');
            controls.className = 'fullscreen-controls';

            const title = document.createElement('h3');
            title.textContent = 'CSV Results';

            const exitBtn = document.createElement('button');
            exitBtn.className = 'exit-fullscreen';
            exitBtn.innerHTML = '<i class="bi bi-x-lg me-1"></i> Exit Fullscreen';

            exitBtn.addEventListener('click', function() {
                document.body.removeChild(fullscreenContainer);
                document.body.style.overflow = '';
            });

            controls.appendChild(title);
            controls.appendChild(exitBtn);

            // Clone the table responsive container
            const tableContainer = document.querySelector('.table-responsive').cloneNode(true);

            // Add to fullscreen
            fullscreenContainer.appendChild(controls);
            fullscreenContainer.appendChild(tableContainer);

            // Prevent body scrolling
            document.body.style.overflow = 'hidden';

            // Add to body
            document.body.appendChild(fullscreenContainer);
        });
    }
});