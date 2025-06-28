document.addEventListener('DOMContentLoaded', function() {
    // Onboarding elements
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    const nextBtn1 = document.getElementById('next-btn-1');
    const nextBtn2 = document.getElementById('next-btn-2');
    const startBtn = document.getElementById('start-btn');
    
    // Loading and result elements
    const loadingSection = document.getElementById('loading-section');
    const resultSection = document.getElementById('result-section');
    const loadingMessage = document.getElementById('loading-message');
    const resultContent = document.getElementById('result-content');
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

    // Step 2 -> Step 3 transition
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

    // Step 3 -> Loading -> Results flow
    async function startProcessing() {
        const activity = activityInput.value.trim();
        if (!activity) {
            activityInput.focus();
            activityInput.classList.add('is-invalid');
            setTimeout(() => activityInput.classList.remove('is-invalid'), 3000);
            return;
        }

        try {
            // First, show initial response and loading screen
            const submitResponse = await fetch('/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: userName,
                    activity: activity
                })
            });
            
            const submitData = await submitResponse.json();
            
            if (submitData.success) {
                // Hide onboarding and show loading
                step3.classList.add('slide-left');
                setTimeout(() => {
                    step3.classList.add('d-none');
                    loadingSection.classList.remove('d-none');
                    loadingMessage.textContent = submitData.message;
                }, 800);

                // Start background processing
                processInBackground();
            } else {
                alert(submitData.message || 'Something went wrong. Please try again.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Network error. Please check your connection and try again.');
        }
    }

    async function processInBackground() {
        try {
            const response = await fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: userName,
                    activity: activityInput.value.trim()
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Hide loading and show results
                loadingSection.classList.add('d-none');
                resultSection.classList.remove('d-none');
                resultContent.textContent = data.result;
            } else {
                // Show error in result section
                loadingSection.classList.add('d-none');
                resultSection.classList.remove('d-none');
                resultContent.textContent = 'Sorry, there was an error processing your request: ' + (data.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Error:', error);
            // Show error in result section
            loadingSection.classList.add('d-none');
            resultSection.classList.remove('d-none');
            resultContent.textContent = 'Network error. Please check your connection and try again.';
        }
    }

    startBtn.addEventListener('click', startProcessing);
    activityInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            startProcessing();
        }
    });

    // Handle restart button
    restartBtn.addEventListener('click', function() {
        // Reset all inputs
        nameInput.value = '';
        activityInput.value = '';
        userName = '';
        
        // Clear result content
        resultContent.textContent = '';
        
        // Reset to step 1
        loadingSection.classList.add('d-none');
        resultSection.classList.add('d-none');
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