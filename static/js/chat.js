$(document).ready(function() {
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
            
            // Add message content in a span for better copying
            const messageContent = $('<span>').text(message);
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
        $('#chat-messages').empty();
        // Add initial bot message
        addMessage("🚀 I'm AuraAI, the digital offspring of Dr. James Utley, PhD—your personal cellular therapy AI expert! 🧠 Whether you're assisting a patient explore treatment or a sales pro mastering the craft, I'm here to make regenerative medicine easy. Let's get started! ⚡", false);
    });

    // Clear Chat
    $('#clear-chat').click(function() {
        if (confirm('Are you sure you want to clear this chat?')) {
            $('#chat-messages').empty();
            // Add initial bot message
            addMessage("Chat cleared. How may I assist you?", false);
        }
    });

    // Export chat functionality
    $('#export-chat').click(function() {
        const messages = [];
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        
        $('#chat-messages .message').each(function() {
            const isUser = $(this).hasClass('user-message');
            const content = isUser ? $(this).text() : $(this).contents().last().text();
            messages.push({
                role: isUser ? 'User' : 'Assistant',
                content: content.trim(),
                timestamp: new Date().toISOString()
            });
        });
        
        if (messages.length === 0) {
            alert('No messages to export');
            return;
        }
        
        // Format the chat content
        const chatContent = messages.map(msg => 
            `[${msg.timestamp}]\n${msg.role}: ${msg.content}\n`
        ).join('\n');
        
        // Create and download the file
        const blob = new Blob([chatContent], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${timestamp}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    });
}); 