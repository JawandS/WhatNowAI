document.addEventListener('DOMContentLoaded', function() {
    // Onboarding elements
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    const nextBtn1 = document.getElementById('next-btn-1');
    const nextBtn2 = document.getElementById('next-btn-2');
    const startBtn = document.getElementById('start-btn');
    
    // Chat elements
    const chatSection = document.getElementById('chat-section');
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const restartBtn = document.getElementById('restart-btn');
    
    // Form inputs
    const nameInput = document.getElementById('user-name');
    const activityInput = document.getElementById('user-activity');
    
    let userName = '';

    // Step 1 -> Step 2 transition
    nextBtn1.addEventListener('click', function() {
        step1.classList.add('slide-left');
        setTimeout(() => {
            step1.classList.add('d-none');
            step2.classList.remove('d-none');
            step2.classList.add('fade-in');
            nameInput.focus();
        }, 800);
    });

    // Step 2 -> Step 3 transition (Enter key or button)
    function goToStep3() {
        const name = nameInput.value.trim();
        if (!name) {
            nameInput.focus();
            nameInput.classList.add('is-invalid');
            setTimeout(() => nameInput.classList.remove('is-invalid'), 3000);
            return;
        }
        
        userName = name;
        step2.classList.add('slide-left');
        setTimeout(() => {
            step2.classList.add('d-none');
            step3.classList.remove('d-none');
            step3.classList.add('fade-in');
            activityInput.focus();
        }, 800);
    }

    nextBtn2.addEventListener('click', goToStep3);
    nameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            goToStep3();
        }
    });

    // Step 3 -> Chat transition (Enter key or button)
    async function startChat() {
        const activity = activityInput.value.trim();
        if (!activity) {
            activityInput.focus();
            activityInput.classList.add('is-invalid');
            setTimeout(() => activityInput.classList.remove('is-invalid'), 3000);
            return;
        }

        try {
            const response = await fetch('/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: userName,
                    activity: activity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Hide onboarding and show chat
                step3.classList.add('slide-left');
                setTimeout(() => {
                    step3.classList.add('d-none');
                    chatSection.classList.remove('d-none');
                    
                    // Add initial messages to chat
                    addMessage(`Hi! My name is ${userName} and I want to ${activity}`, 'user');
                    addMessage(data.message, 'bot');
                    
                    // Focus on chat input
                    userInput.focus();
                }, 800);
            } else {
                alert(data.message || 'Something went wrong. Please try again.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Network error. Please check your connection and try again.');
        }
    }

    startBtn.addEventListener('click', startChat);
    activityInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            startChat();
        }
    });

    // Chat functionality (same as before)
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, 'user');
        userInput.value = '';
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                addMessage(data.response, 'bot');
            } else {
                addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Network error. Please check your connection.', 'bot');
        }
    }

    // Add message to chat box
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;
        
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Handle send button click
    sendBtn.addEventListener('click', sendMessage);

    // Handle Enter key in chat input
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Handle restart button
    restartBtn.addEventListener('click', function() {
        // Reset all inputs
        nameInput.value = '';
        activityInput.value = '';
        userName = '';
        
        // Clear chat
        chatBox.innerHTML = '';
        
        // Reset to step 1
        chatSection.classList.add('d-none');
        step2.classList.add('d-none');
        step3.classList.add('d-none');
        
        step1.classList.remove('d-none', 'slide-left');
        step2.classList.remove('fade-in', 'slide-left');
        step3.classList.remove('fade-in', 'slide-left');
        
        // Focus on first step
        setTimeout(() => {
            nextBtn1.focus();
        }, 100);
    });
});