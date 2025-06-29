document.addEventListener('DOMContentLoaded', function() {
    // Onboarding elements
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    const step4 = document.getElementById('step-4');
    const nextBtn1 = document.getElementById('next-btn-1');
    const nextBtn2 = document.getElementById('next-btn-2');
    const nextBtn3 = document.getElementById('next-btn-3');
    const getLocationBtn = document.getElementById('get-location-btn');
    
    // Loading and result elements
    const loadingSection = document.getElementById('loading-section');
    const resultSection = document.getElementById('result-section');
    const loadingMessage = document.getElementById('loading-message');
    const resultContent = document.getElementById('result-content');
    const restartBtn = document.getElementById('restart-btn');
    
    // Location elements
    const locationSpinner = document.getElementById('location-spinner');
    const locationMessage = document.getElementById('location-message');
    
    // Form inputs
    const nameInput = document.getElementById('user-name');
    const activityInput = document.getElementById('user-activity');
    const cityInput = document.getElementById('user-city');
    const stateInput = document.getElementById('user-state');
    const twitterInput = document.getElementById('user-twitter');
    const instagramInput = document.getElementById('user-instagram');
    const githubInput = document.getElementById('user-github');
    const linkedinInput = document.getElementById('user-linkedin');
    const tiktokInput = document.getElementById('user-tiktok');
    const youtubeInput = document.getElementById('user-youtube');
    
    let userName = '';
    let userSocial = {};
    let userLocation = null;

    // TTS functionality
    async function playIntroductionTTS(step, locationData = null) {
        try {
            const requestBody = locationData ? { location: locationData } : {};
            
            const response = await fetch(`/tts/introduction/${step}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });
            
            const data = await response.json();
            
            if (data.success && data.audio_id) {
                const audio = new Audio(`/audio/${data.audio_id}`);
                
                // Auto-play with user interaction fallback
                try {
                    await audio.play();
                    console.log(`Playing TTS for step: ${step}`);
                } catch (e) {
                    console.log('Auto-play blocked, user interaction required');
                    // Could show a play button here if needed
                }
            } else {
                console.error('Failed to get TTS audio:', data.message);
            }
        } catch (error) {
            console.error('Error playing introduction TTS:', error);
        }
    }

    // Function to play welcome message (after user interaction)
    function playWelcomeIfNeeded() {
        // Welcome audio removed - this function is now empty but kept for compatibility
    }

    // Step 1 -> Step 2 transition
	window.addEventListener('keypress', (event) => {
		if((event.code == "Space" || event.code == "Enter") && !step1.classList.contains('slide-left')) {
			step1.classList.add('slide-left');
			setTimeout(() => {
				step1.classList.add('d-none');
				step2.classList.remove('d-none');
				step2.classList.add('fade-in');
				nameInput.focus();
				
				// Play step name instructions
				setTimeout(() => {
					playIntroductionTTS('step_name');
				}, 500);
			}, 800);
		}
	});
	
    nextBtn1.addEventListener('click', function() {
        step1.classList.add('slide-left');
        setTimeout(() => {
            step1.classList.add('d-none');
            step2.classList.remove('d-none');
            step2.classList.add('fade-in');
            nameInput.focus();
            
            // Play step name instructions
            setTimeout(() => {
                playIntroductionTTS('step_name');
            }, 500);
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
        
        // Capture social media handles (optional)
        userSocial = {
            twitter: twitterInput.value.trim().replace('@', ''), // Remove @ if user added it
            instagram: instagramInput.value.trim().replace('@', ''), // Remove @ if user added it
            github: githubInput.value.trim().replace('@', ''), // Remove @ if user added it
            linkedin: linkedinInput.value.trim().replace('@', ''), // Remove @ if user added it
            tiktok: tiktokInput.value.trim().replace('@', ''), // Remove @ if user added it
            youtube: youtubeInput.value.trim().replace('@', '') // Remove @ if user added it
        };
        
        step2.classList.add('slide-left');
        setTimeout(() => {
            step2.classList.add('d-none');
            step3.classList.remove('d-none');
            step3.classList.add('fade-in');
            activityInput.focus();
            
            // Play step activity instructions
            setTimeout(() => {
                playIntroductionTTS('step_activity');
            }, 500);
        }, 800);
    }

    nextBtn2.addEventListener('click', goToStep3);
    nameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            goToStep3();
        }
    });

    // Step 3 -> Step 4 transition
    function goToStep4() {
        const activity = activityInput.value.trim();
        if (!activity) {
            activityInput.focus();
            activityInput.classList.add('is-invalid');
            setTimeout(() => activityInput.classList.remove('is-invalid'), 3000);
            return;
        }
        
        step3.classList.add('slide-left');
        setTimeout(() => {
            step3.classList.add('d-none');
            step4.classList.remove('d-none');
            step4.classList.add('fade-in');
            cityInput.focus();
            
            // Play step location instructions
            setTimeout(() => {
                playIntroductionTTS('step_location');
            }, 500);
        }, 800);
    }

    nextBtn3.addEventListener('click', goToStep4);
    activityInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            goToStep4();
        }
    });

    // Location handling - City/State based
    async function processLocation() {
        const city = cityInput.value.trim();
        const state = stateInput.value.trim();
        
        if (!city || !state) {
            if (!city) {
                cityInput.focus();
                cityInput.classList.add('is-invalid');
                setTimeout(() => cityInput.classList.remove('is-invalid'), 3000);
            }
            if (!state) {
                stateInput.focus(); 
                stateInput.classList.add('is-invalid');
                setTimeout(() => stateInput.classList.remove('is-invalid'), 3000);
            }
            return;
        }

        locationSpinner.classList.remove('d-none');
        locationMessage.classList.remove('d-none');
        locationMessage.textContent = 'Processing your location...';
        getLocationBtn.disabled = true;

        try {
            // Forward geocode the city/state to get coordinates and location info
            const response = await fetch('/geocode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    city: city,
                    state: state
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                userLocation = data.location;
                locationSpinner.classList.add('d-none');
                locationMessage.innerHTML = `
                    <div class="text-success">
                        <i class="bi bi-check-circle"></i> 
                        Location found: ${userLocation.city}, ${userLocation.state || userLocation.country}
                    </div>
                `;
                
                // Auto-proceed to processing after a short delay
                setTimeout(() => {
                    startProcessing();
                }, 1500);
                
            } else {
                throw new Error(data.message || 'Failed to find location');
            }
            
        } catch (error) {
            console.error('Geocoding error:', error);
            locationSpinner.classList.add('d-none');
            locationMessage.innerHTML = `<div class="text-warning">Unable to find location. Please check your city and state and try again.</div>`;
            getLocationBtn.disabled = false;
        }
    }

    // Handle Enter key in city/state inputs
    cityInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            stateInput.focus();
        }
    });
    
    stateInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            processLocation();
        }
    });


    // Event listeners for location button
    getLocationBtn.addEventListener('click', processLocation);

    // Step 4 -> Processing flow
    async function startProcessing() {
        if (!userLocation) {
            locationMessage.innerHTML = `<div class="text-warning">Please enter your city and state first.</div>`;
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
                    activity: activityInput.value.trim(),
                    social: userSocial
                })
            });
            
            const submitData = await submitResponse.json();
            
            if (submitData.success) {
                // Hide onboarding and show loading
                step4.classList.add('slide-left');
                setTimeout(() => {
                    step4.classList.add('d-none');
                    loadingSection.classList.remove('d-none');
                    loadingMessage.textContent = submitData.message;
                    
                    // Play processing instructions with location context
                    setTimeout(() => {
                        playIntroductionTTS('processing', userLocation);
                    }, 500);
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
                    activity: activityInput.value.trim(),
                    location: userLocation,
                    social: userSocial
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Check if we should redirect to map
                if (data.redirect_to_map && data.map_url) {
                    // Store user data for the map page with enhanced personalization data
                    sessionStorage.setItem('userData', JSON.stringify({
                        name: userName,
                        activity: activityInput.value.trim(),
                        location: userLocation,
                        social: userSocial,
                        searchResults: data.search_summaries,
                        personalization_data: data.personalization_data  // Include personalization data
                    }));
                    
                    // Redirect to map page
                    window.location.href = data.map_url;
                } else {
                    // Hide loading and show results
                    loadingSection.classList.add('d-none');
                    resultSection.classList.remove('d-none');
                    resultContent.textContent = data.result;
                }
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

    // Handle restart button
    restartBtn.addEventListener('click', function() {
        // Reset all inputs and variables
        nameInput.value = '';
        activityInput.value = '';
        cityInput.value = '';
        stateInput.value = '';
        twitterInput.value = '';
        instagramInput.value = '';
        userName = '';
        userSocial = {};
        userLocation = null;
        
        // Reset location UI
        locationSpinner.classList.add('d-none');
        locationMessage.classList.add('d-none');
        locationMessage.textContent = '';
        getLocationBtn.disabled = false;
        getLocationBtn.textContent = 'Continue';
        
        // Clear result content
        resultContent.textContent = '';
        
        // Reset to step 1
        loadingSection.classList.add('d-none');
        resultSection.classList.add('d-none');
        step2.classList.add('d-none');
        step3.classList.add('d-none');
        step4.classList.add('d-none');
        
        step1.classList.remove('d-none', 'slide-left');
        step2.classList.remove('fade-in', 'slide-left');
        step3.classList.remove('fade-in', 'slide-left');
        step4.classList.remove('fade-in', 'slide-left');
        
        // Focus on first step
        setTimeout(() => {
            nextBtn1.focus();
        }, 100);
    });
});

