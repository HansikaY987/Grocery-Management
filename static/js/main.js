/**
 * SmartCartPro - Main JavaScript file
 * Handles common functionality across the application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flash Messages (auto-hide after 5 seconds)
    initializeFlashMessages();
    
    // Initialize notifications polling
    if (document.querySelector('.notifications-badge')) {
        fetchUnreadNotificationsCount();
        // Poll every 60 seconds for new notifications
        setInterval(fetchUnreadNotificationsCount, 60000);
    }
    
    // Initialize hover animations on product cards
    initProductCardAnimations();
    
    // Initialize medical warnings
    initMedicalWarnings();
});

/**
 * Initialize flash message auto-hide functionality
 */
function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        // Hide message after 5 seconds
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
        
        // Add close button functionality
        const closeButton = message.querySelector('.close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                message.style.opacity = '0';
                setTimeout(() => {
                    message.style.display = 'none';
                }, 500);
            });
        }
    });
}

/**
 * Fetch unread notifications count and update badge
 */
function fetchUnreadNotificationsCount() {
    fetch('/api/notifications/unread')
        .then(response => response.json())
        .then(data => {
            const badge = document.querySelector('.notifications-badge');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count > 99 ? '99+' : data.count;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('Error fetching notifications:', error));
}

/**
 * Initialize hover animations on product cards
 */
function initProductCardAnimations() {
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.classList.add('glow-effect');
        });
        
        card.addEventListener('mouseleave', () => {
            card.classList.remove('glow-effect');
        });
    });
}

/**
 * Initialize medical warnings tooltips and interactions
 */
function initMedicalWarnings() {
    const warningElements = document.querySelectorAll('.product-warning');
    
    warningElements.forEach(element => {
        // Make warnings more interactive
        element.addEventListener('mouseenter', () => {
            element.classList.add('pulse-effect');
        });
        
        element.addEventListener('mouseleave', () => {
            element.classList.remove('pulse-effect');
        });
    });
    
    // Initialize medical interaction checking for cart page
    const cartMedicalCheck = document.getElementById('cart-medical-check');
    if (cartMedicalCheck) {
        cartMedicalCheck.addEventListener('click', checkMedicalInteractions);
    }
}

/**
 * Check for medical interactions between cart items
 */
function checkMedicalInteractions() {
    const medicalAlertContainer = document.getElementById('medical-alerts');
    if (!medicalAlertContainer) return;
    
    // Collect product IDs from cart
    const productIds = Array.from(document.querySelectorAll('[data-product-id]'))
        .map(el => parseInt(el.dataset.productId));
    
    if (productIds.length <= 1) {
        medicalAlertContainer.innerHTML = '<div class="alert alert-info">No potential interactions to check with a single item.</div>';
        return;
    }
    
    // Show loading indicator
    medicalAlertContainer.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p>Checking for potential medication interactions...</p></div>';
    
    // Call API to check interactions
    fetch('/api/ai/medical-interaction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ product_ids: productIds }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            medicalAlertContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        // Display warnings
        if (data.status === 'warning' && data.interactions.length > 0) {
            let warningHtml = '<div class="alert alert-warning"><h5>Potential Medication Interactions Detected</h5><ul>';
            data.interactions.forEach(warning => {
                warningHtml += `<li>${warning}</li>`;
            });
            warningHtml += '</ul><p class="mt-2 mb-0"><small>Always consult with your healthcare provider before making changes to your medication regimen.</small></p></div>';
            medicalAlertContainer.innerHTML = warningHtml;
        } else {
            medicalAlertContainer.innerHTML = '<div class="alert alert-success">No significant interactions detected between these items.</div>';
        }
    })
    .catch(error => {
        console.error('Error checking medical interactions:', error);
        medicalAlertContainer.innerHTML = '<div class="alert alert-danger">Failed to check for medication interactions. Please try again.</div>';
    });
}

/**
 * Format currency with 2 decimal places
 * @param {number} amount - The amount to format
 * @returns {string} - Formatted currency string
 */
function formatCurrency(amount) {
    return '$' + parseFloat(amount).toFixed(2);
}

/**
 * Format date to readable string
 * @param {string} dateString - Date string to format
 * @returns {string} - Formatted date string
 */
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}
