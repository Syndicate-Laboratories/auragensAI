$(document).ready(function() {
    const WELCOME_MESSAGE = `<div class="message bot-message">
        <img src="/static/js/Auragens_chat.svg" alt="Auragens Chat Logo" class="chat-logo">
        🚀 I'm Auragens-AI, the digital offspring of Dr. James Utley, PhD—your personal cellular therapy AI expert! I am here to answer all your questions about stem cell therapy. 🧠 Let's get started! ⚡
    </div>`;

    function addMessage(message, isUser) {
        const messageDiv = $('<div></div>')
            .addClass('message')
            .addClass(isUser ? 'user-message' : 'bot-message');
        
        // Add logo for bot messages
        if (!isUser) {
            const logoImg = $('<img>')
                .attr('src', '/static/js/Auragens_chat.svg')
                .attr('alt', 'Auragens Chat Logo')
                .addClass('chat-logo');
            messageDiv.append(logoImg);
            
            // Changed from span to div for better formatting
            const messageContent = $('<div>')  // Changed from span to div
                .addClass('message-content')   // Added class for styling
                .html(message);               // Using html() to preserve formatting
            messageDiv.append(messageContent);
            
            // Add feedback and copy buttons
            const actionsDiv = $('<div>').addClass('message-actions');
            
            // Add copy button
            const copyButton = $('<i>')
                .addClass('fas fa-copy copy-button')
                .attr('title', 'Copy message')
                .click(function(e) {
                    e.stopPropagation();
                    navigator.clipboard.writeText(message).then(() => {
                        // Temporarily change icon to show success
                        $(this).removeClass('fa-copy').addClass('fa-check');
                        setTimeout(() => {
                            $(this).removeClass('fa-check').addClass('fa-copy');
                        }, 1500);
                    });
                });
            
            // Add like/dislike buttons
            const likeButton = $('<i>')
                .addClass('fas fa-thumbs-up feedback-icon')
                .attr('title', 'Helpful')
                .click(function(e) {
                    e.stopPropagation();
                    $(this).toggleClass('liked');
                    $(this).siblings('.fa-thumbs-down').removeClass('disliked');
                    // Here you could add AJAX call to save feedback
                });
            
            const dislikeButton = $('<i>')
                .addClass('fas fa-thumbs-down feedback-icon')
                .attr('title', 'Not helpful')
                .click(function(e) {
                    e.stopPropagation();
                    $(this).toggleClass('disliked');
                    $(this).siblings('.fa-thumbs-up').removeClass('liked');
                    // Here you could add AJAX call to save feedback
                });
            
            actionsDiv.append(copyButton, likeButton, dislikeButton);
            messageDiv.append(actionsDiv);
        } else {
            messageDiv.text(message);
        }
        $('#chat-messages').append(messageDiv);
        $('#chat-messages').scrollTop($('#chat-messages')[0].scrollHeight);
    }

    function sendMessage() {
        const userInput = $('#user-input');
        const message = userInput.val().trim();
        
        if (message) {
            addMessage(message, true);
            userInput.val('');
            
            // Disable input while waiting for response
            userInput.prop('disabled', true);
            $('#send-button').prop('disabled', true);
            
            // Add loading dots
            const loadingDots = $(`
                <div class="loading-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            `);
            $('#chat-messages').append(loadingDots);
            $('#chat-messages').scrollTop($('#chat-messages')[0].scrollHeight);
            
            // Send message to server
            $.ajax({
                url: '/chat',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ message: message }),
                success: function(response) {
                    // Remove loading dots
                    loadingDots.remove();
                    addMessage(response.response, false);
                },
                error: function() {
                    // Remove loading dots
                    loadingDots.remove();
                    addMessage("Sorry, there was an error processing your request.", false);
                },
                complete: function() {
                    userInput.prop('disabled', false);
                    $('#send-button').prop('disabled', false);
                    userInput.focus();
                }
            });
        }
    }

    // Send message on button click
    $('#send-button').click(sendMessage);

    // Send message on Enter key
    $('#user-input').keypress(function(e) {
        if (e.which == 13) {
            sendMessage();
        }
    });

    // Menu Toggle
    $('.menu-button').click(function(e) {
        e.stopPropagation();
        $('.menu-dropdown').toggleClass('show');
    });

    // Close menu when clicking outside
    $(document).click(function() {
        $('.menu-dropdown').removeClass('show');
    });

    // New Chat
    $('#new-chat').click(function() {
        $('#chat-messages').empty();  // Clear all messages
        // Add back the welcome message
        $('#chat-messages').html(WELCOME_MESSAGE);
    });

    // Clear Chat
    $('#clear-chat').click(function() {
        if (confirm('Are you sure you want to clear this chat?')) {
            $('#chat-messages').empty();  // Clear all messages
            // Add back only the welcome message
            $('#chat-messages').html(WELCOME_MESSAGE);
        }
    });

    // Export chat functionality
    $('#export-chat').click(function() {
        const chatMessages = document.querySelectorAll('.message');
        let exportText = "Auragens AI Chat Export\n";
        exportText += "Generated: " + new Date().toLocaleString() + "\n\n";
        
        chatMessages.forEach((message) => {
            if (message.classList.contains('user-message')) {
                exportText += "User: " + message.textContent + "\n";
            } else if (message.classList.contains('bot-message')) {
                // Remove the logo text content if present
                const botText = message.querySelector('.chat-logo') 
                    ? message.textContent.replace(message.querySelector('.chat-logo').textContent, '').trim()
                    : message.textContent;
                exportText += "Auragens AI: " + botText + "\n";
            }
            exportText += "\n";
        });
        
        // Create blob and download
        const blob = new Blob([exportText], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'auragens-chat-export-' + new Date().toISOString().slice(0,10) + '.txt';
        a.click();
        window.URL.revokeObjectURL(url);
    });
}); 