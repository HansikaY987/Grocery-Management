/**
 * SmartCartPro - AI Chatbot
 * Handles interaction with the Gemini AI chatbot
 */

let chatbotOpen = false;
let dragging = false;
let offsetX, offsetY;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize chatbot
    initChatbot();
    
    // Make chatbot draggable
    makeChatbotDraggable();
});

/**
 * Initialize chatbot functionality
 */
function initChatbot() {
    const chatbotIcon = document.getElementById('chatbot-icon');
    const chatbotContainer = document.getElementById('chatbot-container');
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotMessages = document.getElementById('chatbot-messages');
    
    // If chatbot elements don't exist, return
    if (!chatbotIcon || !chatbotContainer) return;
    
    // Toggle chatbot when icon is clicked
    chatbotIcon.addEventListener('click', function() {
        toggleChatbot();
    });
    
    // Toggle minimize/maximize when toggle button is clicked
    if (chatbotToggle) {
        chatbotToggle.addEventListener('click', function() {
            chatbotContainer.classList.toggle('chatbot-minimize');
        });
    }
    
    // Handle chatbot form submission
    if (chatbotForm && chatbotInput && chatbotMessages) {
        chatbotForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const userMessage = chatbotInput.value.trim();
            
            if (!userMessage) return;
            
            // Add user message to chat
            addMessage(userMessage, 'user');
            
            // Clear input
            chatbotInput.value = '';
            
            // Show typing indicator
            addTypingIndicator();
            
            // Send message to AI endpoint
            sendMessageToAI(userMessage);
        });
        
        // Add initial greeting message
        setTimeout(() => {
            addMessage("👋 Hello! I'm your SmartCartPro assistant. I can help with health queries, grocery recommendations, or medication information. What can I help you with today?", 'bot');
        }, 500);
    }
}

/**
 * Toggle chatbot visibility
 */
function toggleChatbot() {
    const chatbotIcon = document.getElementById('chatbot-icon');
    const chatbotContainer = document.getElementById('chatbot-container');
    
    if (!chatbotContainer || !chatbotIcon) return;
    
    chatbotOpen = !chatbotOpen;
    
    if (chatbotOpen) {
        // Show chatbot container
        chatbotContainer.style.display = 'flex';
        chatbotIcon.style.display = 'none';
        
        // Force scroll to bottom of messages
        scrollChatToBottom();
        
        // Focus input
        setTimeout(() => {
            const input = document.getElementById('chatbot-input');
            if (input) input.focus();
        }, 100);
    } else {
        // Hide chatbot container
        chatbotContainer.style.display = 'none';
        chatbotIcon.style.display = 'flex';
    }
}

/**
 * Add message to the chat
 * @param {string} message - The message text
 * @param {string} sender - 'user' or 'bot'
 */
function addMessage(message, sender) {
    const chatbotMessages = document.getElementById('chatbot-messages');
    if (!chatbotMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
    
    // Process markdown-like formatting for bot messages
    if (sender === 'bot') {
        // Convert **bold** to <strong>
        message = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to <em>
        message = message.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert URLs to links
        message = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
        
        // Convert bullet points
        message = message.replace(/^- (.*)/gm, '• $1');
        
        // Convert line breaks
        message = message.replace(/\n/g, '<br>');
    } else {
        // Escape HTML for user messages
        message = message.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    messageElement.innerHTML = message;
    chatbotMessages.appendChild(messageElement);
    
    // Scroll to bottom
    scrollChatToBottom();
}

/**
 * Add typing indicator to the chat
 */
function addTypingIndicator() {
    const chatbotMessages = document.getElementById('chatbot-messages');
    if (!chatbotMessages) return;
    
    const indicator = document.createElement('div');
    indicator.classList.add('message', 'bot-message', 'typing-indicator');
    indicator.innerHTML = '<span></span><span></span><span></span>';
    indicator.id = 'typing-indicator';
    
    chatbotMessages.appendChild(indicator);
    
    // Scroll to bottom
    scrollChatToBottom();
}

/**
 * Remove typing indicator from the chat
 */
function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Scroll chat to the bottom
 */
function scrollChatToBottom() {
    const chatbotMessages = document.getElementById('chatbot-messages');
    if (chatbotMessages) {
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }
}

/**
 * Send message to AI endpoint
 * @param {string} message - The user's message
 */
function sendMessageToAI(message) {
    fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: message }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Remove typing indicator
        removeTypingIndicator();
        
        if (data.error) {
            addMessage("I'm sorry, I'm having trouble connecting to my brain right now. Please try again later.", 'bot');
            console.error('AI response error:', data.error);
            return;
        }
        
        // Add AI response
        addMessage(data.response, 'bot');
    })
    .catch(error => {
        // Remove typing indicator
        removeTypingIndicator();
        
        // Show error message
        addMessage("I'm sorry, I couldn't process your request. Please try again later.", 'bot');
        console.error('Error:', error);
    });
}

/**
 * Make the chatbot container draggable
 */
function makeChatbotDraggable() {
    const chatbotContainer = document.getElementById('chatbot-container');
    const chatbotHeader = document.getElementById('chatbot-header');
    
    if (!chatbotContainer || !chatbotHeader) return;
    
    chatbotHeader.addEventListener('mousedown', function(e) {
        // Only start dragging if not clicking on the toggle button
        if (e.target.id !== 'chatbot-toggle' && !e.target.closest('#chatbot-toggle')) {
            dragging = true;
            
            // Calculate offset
            const rect = chatbotContainer.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            
            // Add dragging class
            chatbotContainer.classList.add('dragging');
        }
    });
    
    document.addEventListener('mousemove', function(e) {
        if (dragging) {
            // Calculate new position
            let newLeft = e.clientX - offsetX;
            let newTop = e.clientY - offsetY;
            
            // Constrain to window boundaries
            const maxX = window.innerWidth - chatbotContainer.offsetWidth;
            const maxY = window.innerHeight - chatbotContainer.offsetHeight;
            
            newLeft = Math.max(0, Math.min(newLeft, maxX));
            newTop = Math.max(0, Math.min(newTop, maxY));
            
            // Set new position
            chatbotContainer.style.left = newLeft + 'px';
            chatbotContainer.style.top = newTop + 'px';
        }
    });
    
    document.addEventListener('mouseup', function() {
        if (dragging) {
            dragging = false;
            
            // Remove dragging class
            chatbotContainer.classList.remove('dragging');
        }
    });
}
