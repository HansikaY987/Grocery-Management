/**
 * SmartCartPro - Cart functionality
 * Handles shopping cart interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize quantity controls
    initQuantityControls();
    
    // Initialize coupon functionality
    initCouponForm();
    
    // Initialize cart totals calculations
    calculateCartTotals();
});

/**
 * Initialize quantity increment/decrement controls
 */
function initQuantityControls() {
    const decrementButtons = document.querySelectorAll('.quantity-btn-decrease');
    const incrementButtons = document.querySelectorAll('.quantity-btn-increase');
    const quantityInputs = document.querySelectorAll('.quantity-input');
    
    // Add event listeners to decrement buttons
    decrementButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentNode.querySelector('.quantity-input');
            const currentValue = parseInt(input.value);
            
            if (currentValue > 1) {
                input.value = currentValue - 1;
                // Update item subtotal
                updateItemSubtotal(input);
                // Update cart totals
                calculateCartTotals();
            }
        });
    });
    
    // Add event listeners to increment buttons
    incrementButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentNode.querySelector('.quantity-input');
            const currentValue = parseInt(input.value);
            const maxStock = parseInt(input.dataset.maxStock || 999);
            
            if (currentValue < maxStock) {
                input.value = currentValue + 1;
                // Update item subtotal
                updateItemSubtotal(input);
                // Update cart totals
                calculateCartTotals();
            } else {
                // Display max stock warning
                alert(`Sorry, only ${maxStock} items available in stock.`);
            }
        });
    });
    
    // Add event listeners to quantity inputs
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const currentValue = parseInt(this.value);
            const maxStock = parseInt(this.dataset.maxStock || 999);
            
            // Ensure value is at least 1
            if (isNaN(currentValue) || currentValue < 1) {
                this.value = 1;
            }
            
            // Ensure value does not exceed max stock
            if (currentValue > maxStock) {
                this.value = maxStock;
                // Display max stock warning
                alert(`Sorry, only ${maxStock} items available in stock.`);
            }
            
            // Update item subtotal
            updateItemSubtotal(this);
            // Update cart totals
            calculateCartTotals();
        });
    });
}

/**
 * Update item subtotal based on quantity and price
 * @param {HTMLElement} input - The quantity input element
 */
function updateItemSubtotal(input) {
    const cartItem = input.closest('.cart-item');
    const quantity = parseInt(input.value);
    const price = parseFloat(cartItem.dataset.price);
    const subtotalElement = cartItem.querySelector('.cart-item-subtotal');
    
    const subtotal = quantity * price;
    subtotalElement.textContent = formatCurrency(subtotal);
    
    // Update hidden input for form submission
    const hiddenInput = cartItem.querySelector('input[name="quantity"]');
    if (hiddenInput) {
        hiddenInput.value = quantity;
    }
}

/**
 * Calculate and update cart totals
 */
function calculateCartTotals() {
    const cartItems = document.querySelectorAll('.cart-item');
    let subtotal = 0;
    
    // Calculate subtotal
    cartItems.forEach(item => {
        const price = parseFloat(item.dataset.price);
        const quantity = parseInt(item.querySelector('.quantity-input').value);
        subtotal += price * quantity;
    });
    
    // Update subtotal display
    const subtotalElement = document.getElementById('cart-subtotal');
    if (subtotalElement) {
        subtotalElement.textContent = formatCurrency(subtotal);
    }
    
    // Calculate discount (if applicable)
    let discount = 0;
    const discountElement = document.getElementById('cart-discount');
    if (discountElement) {
        discount = parseFloat(discountElement.dataset.value || 0);
        discountElement.textContent = formatCurrency(discount);
    }
    
    // Calculate total
    const total = subtotal - discount;
    const totalElement = document.getElementById('cart-total');
    if (totalElement) {
        totalElement.textContent = formatCurrency(total);
    }
}

/**
 * Initialize coupon form functionality
 */
function initCouponForm() {
    const couponForm = document.getElementById('coupon-form');
    const couponResult = document.getElementById('coupon-result');
    
    if (couponForm) {
        couponForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const couponCode = this.querySelector('input[name="coupon_code"]').value.trim();
            
            if (!couponCode) {
                couponResult.innerHTML = '<div class="alert alert-danger">Please enter a coupon code.</div>';
                return;
            }
            
            // Submit the form through regular form submission
            this.submit();
        });
    }
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
 * Handle remove item confirmation
 * @param {number} itemId - The cart item ID to remove
 */
function confirmRemoveItem(itemId) {
    if (confirm('Are you sure you want to remove this item from your cart?')) {
        document.getElementById('remove-form-' + itemId).submit();
    }
}

/**
 * Move an item from wishlist to cart
 * @param {number} itemId - The wishlist item ID
 */
function moveToCart(itemId) {
    document.getElementById('move-to-cart-form-' + itemId).submit();
}

/**
 * Remove an item from wishlist
 * @param {number} itemId - The wishlist item ID
 */
function removeFromWishlist(itemId) {
    if (confirm('Are you sure you want to remove this item from your wishlist?')) {
        document.getElementById('remove-wishlist-form-' + itemId).submit();
    }
}
