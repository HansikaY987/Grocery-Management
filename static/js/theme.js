/**
 * SmartCartPro - Theme Switcher
 * Handles dark/light mode toggling with smooth transitions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme based on localStorage or system preference
    initializeTheme();
    
    // Add event listener to theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', toggleTheme);
    }
});

/**
 * Initialize theme based on user preference or system setting
 */
function initializeTheme() {
    // Check localStorage for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
        // Apply saved theme
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        // Update toggle switch
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.checked = savedTheme === 'dark';
        }
    } else {
        // Check if system preference is dark mode
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (prefersDark) {
            document.documentElement.setAttribute('data-theme', 'dark');
            
            // Update toggle switch
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.checked = true;
            }
            
            // Save preference
            localStorage.setItem('theme', 'dark');
        }
    }
    
    // Add transition after initial load (prevents flash during page load)
    setTimeout(() => {
        document.body.classList.add('theme-transition');
    }, 100);
    
    // Add event listener for system preference changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (!localStorage.getItem('theme')) {
                // Only apply if user hasn't manually set preference
                const newTheme = e.matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', newTheme);
                
                // Update toggle switch
                const themeToggle = document.getElementById('theme-toggle');
                if (themeToggle) {
                    themeToggle.checked = e.matches;
                }
            }
        });
    }
}

/**
 * Toggle between dark and light themes
 */
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    // Apply the new theme
    document.documentElement.setAttribute('data-theme', newTheme);
    
    // Save preference to localStorage
    localStorage.setItem('theme', newTheme);
    
    // Apply glitch effect during transition
    applyThemeTransitionEffect();
}

/**
 * Apply glitch effect during theme transition
 */
function applyThemeTransitionEffect() {
    const products = document.querySelectorAll('.product-card');
    
    products.forEach(product => {
        product.classList.add('glitch-effect');
        setTimeout(() => {
            product.classList.remove('glitch-effect');
        }, 500);
    });
    
    // Animate logo
    const logo = document.querySelector('.header-logo');
    if (logo) {
        logo.classList.add('pulse-effect');
        setTimeout(() => {
            logo.classList.remove('pulse-effect');
        }, 500);
    }
}
