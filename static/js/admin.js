/**
 * SmartCartPro - Admin Panel JavaScript
 * Handles functionality specific to the admin dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Initialize charts if they exist
    if (document.getElementById('salesChart')) {
        initCharts();
    }
    
    // Initialize Google Maps for delivery tracking
    if (document.getElementById('deliveryMap')) {
        initDeliveryMap();
    }
    
    // Initialize form validations
    initFormValidations();
    
    // Initialize sortable tables
    initSortableTables();
    
    // Highlight expiry dates
    highlightExpiryDates();
    
    // Initialize date pickers
    initDatePickers();
});

/**
 * Initialize charts for sales and order statistics
 */
function initCharts() {
    // Chart initialization is handled in the specific template files
    console.log('Charts initialized');
}

/**
 * Highlight expiry dates that are approaching
 */
function highlightExpiryDates() {
    const today = new Date();
    
    // Find all expiry date cells with data-expiry attribute
    document.querySelectorAll('[data-expiry]').forEach(function(cell) {
        const expiryDate = new Date(cell.dataset.expiry);
        const daysLeft = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
        
        if (daysLeft <= 0) {
            cell.classList.add('expired');
            cell.closest('tr').classList.add('table-danger');
        } else if (daysLeft <= 30) {
            cell.classList.add('expiring-soon');
            cell.closest('tr').classList.add('table-warning');
        }
    });
}

/**
 * Initialize Google Maps for delivery tracking
 */
function initDeliveryMap() {
    // Check if the Google Maps API is loaded
    if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
        console.error('Google Maps API not loaded');
        document.getElementById('deliveryMap').innerHTML = '<div class="alert alert-warning">Google Maps could not be loaded. Please check your API key.</div>';
        return;
    }
    
    // Get delivery locations from data attribute
    const mapElement = document.getElementById('deliveryMap');
    const deliveryLocations = JSON.parse(mapElement.dataset.locations || '[]');
    
    const map = new google.maps.Map(mapElement, {
        center: { lat: 40.7128, lng: -74.0060 }, // Default to New York City
        zoom: 10
    });
    
    // Add markers for delivery locations
    const bounds = new google.maps.LatLngBounds();
    const infoWindow = new google.maps.InfoWindow();
    
    deliveryLocations.forEach(function(location) {
        const position = { lat: location.lat, lng: location.lng };
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: location.address,
            icon: getMarkerIconForStatus(location.status)
        });
        
        bounds.extend(position);
        
        // Add info window for marker
        marker.addListener('click', function() {
            const content = `
                <div>
                    <h5>Order #${location.order_id}</h5>
                    <p><strong>Customer:</strong> ${location.customer}</p>
                    <p><strong>Address:</strong> ${location.address}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${getStatusBadgeClass(location.status)}">${formatStatus(location.status)}</span></p>
                    <p><strong>Total:</strong> $${location.total.toFixed(2)}</p>
                    <a href="/admin/orders/${location.order_id}" class="btn btn-sm btn-primary">View Order</a>
                </div>
            `;
            
            infoWindow.setContent(content);
            infoWindow.open(map, marker);
        });
    });
    
    // Fit map to bounds if there are markers
    if (deliveryLocations.length > 0) {
        map.fitBounds(bounds);
    }
}

/**
 * Get marker icon based on order status
 * @param {string} status - Order status
 * @returns {string} - URL to the marker icon
 */
function getMarkerIconForStatus(status) {
    switch(status) {
        case 'pending':
            return 'https://maps.google.com/mapfiles/ms/icons/red-dot.png';
        case 'out_for_delivery':
            return 'https://maps.google.com/mapfiles/ms/icons/yellow-dot.png';
        case 'delivered':
            return 'https://maps.google.com/mapfiles/ms/icons/green-dot.png';
        case 'cancelled':
            return 'https://maps.google.com/mapfiles/ms/icons/purple-dot.png';
        default:
            return 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png';
    }
}

/**
 * Get bootstrap badge class based on order status
 * @param {string} status - Order status
 * @returns {string} - Badge class
 */
function getStatusBadgeClass(status) {
    switch(status) {
        case 'pending':
            return 'warning';
        case 'out_for_delivery':
            return 'primary';
        case 'delivered':
            return 'success';
        case 'cancelled':
            return 'danger';
        default:
            return 'secondary';
    }
}

/**
 * Format order status for display
 * @param {string} status - Order status
 * @returns {string} - Formatted status
 */
function formatStatus(status) {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Initialize form validations
 */
function initFormValidations() {
    // Select all forms with data-validate attribute
    document.querySelectorAll('form[data-validate="true"]').forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * Initialize sortable tables
 */
function initSortableTables() {
    // Check if DataTables is available
    if (typeof $.fn.DataTable !== 'undefined') {
        $('table.datatable').DataTable({
            responsive: true
        });
    }
}

/**
 * Sort table by the specified column
 * @param {HTMLElement} table - The table element
 * @param {string} sortKey - The data-sort value of the column to sort by
 * @param {boolean} ascending - Whether to sort in ascending order
 */
function sortTable(table, sortKey, ascending) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Sort rows based on the specified column
    rows.sort((a, b) => {
        const aValue = a.querySelector(`[data-sort="${sortKey}"]`).textContent.trim();
        const bValue = b.querySelector(`[data-sort="${sortKey}"]`).textContent.trim();
        
        if (!isNaN(aValue) && !isNaN(bValue)) {
            return ascending ? aValue - bValue : bValue - aValue;
        }
        
        return ascending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
    });
    
    // Clear the table and add sorted rows
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }
    
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Initialize date pickers
 */
function initDatePickers() {
    // Check if date picker elements exist
    if (document.querySelectorAll('.datepicker').length > 0) {
        // Using native input[type="date"] which is well-supported now
        console.log('Date pickers initialized');
    }
}

/**
 * Confirm action before form submission
 * @param {string} message - Confirmation message
 * @param {string} formId - The ID of the form to submit
 * @returns {boolean} - Whether the action was confirmed
 */
function confirmAction(message, formId) {
    if (confirm(message)) {
        document.getElementById(formId).submit();
        return true;
    }
    return false;
}

/**
 * Update order status
 * @param {number} orderId - The order ID
 * @param {string} status - The new status
 */
function updateOrderStatus(orderId, status) {
    const statusText = formatStatus(status);
    
    if (confirm(`Are you sure you want to update Order #${orderId} to status "${statusText}"?`)) {
        fetch(`/admin/orders/${orderId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            },
            body: JSON.stringify({ status: status })
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Failed to update order status. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error updating order status:', error);
            alert('An error occurred while updating the order status.');
        });
    }
}