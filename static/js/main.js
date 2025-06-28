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
    const skipLocationBtn = document.getElementById('skip-location-btn');
    
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
    
    let userName = '';
    let userLocation = null;

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
        }, 800);
    }

    nextBtn3.addEventListener('click', goToStep4);
    activityInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            goToStep4();
        }
    });

    // Location handling
    async function getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by this browser.'));
                return;
            }

            locationSpinner.classList.remove('d-none');
            locationMessage.textContent = 'Getting your location...';
            getLocationBtn.disabled = true;

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    try {
                        const latitude = position.coords.latitude;
                        const longitude = position.coords.longitude;
                        
                        locationMessage.textContent = 'Analyzing location...';
                        
                        // Reverse geocode the coordinates
                        const response = await fetch('/geocode', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                latitude: latitude,
                                longitude: longitude
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            userLocation = data.location;
                            locationSpinner.classList.add('d-none');
                            locationMessage.innerHTML = `
                                <div class="text-success">
                                    <i class="bi bi-check-circle"></i> 
                                    Location found: ${userLocation.city}, ${userLocation.country}
                                </div>
                            `;
                            
                            // Auto-proceed to processing after a short delay
                            setTimeout(() => {
                                startProcessing();
                            }, 1500);
                            
                        } else {
                            throw new Error(data.message || 'Failed to get location details');
                        }
                        
                    } catch (error) {
                        console.error('Geocoding error:', error);
                        useDefaultLocation();
                    }
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    locationSpinner.classList.add('d-none');
                    
                    let errorMessage = 'Unable to get your location. ';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMessage += 'Location access denied.';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMessage += 'Location information unavailable.';
                            break;
                        case error.TIMEOUT:
                            errorMessage += 'Location request timed out.';
                            break;
                        default:
                            errorMessage += 'Unknown error occurred.';
                            break;
                    }
                    
                    locationMessage.innerHTML = `<div class="text-warning">${errorMessage}</div>`;
                    getLocationBtn.disabled = false;
                    getLocationBtn.textContent = 'Try Again';
                }
            );
        });
    }

    function useDefaultLocation() {
        userLocation = {
            country: 'Global',
            city: 'Unknown',
            zipcode: 'Unknown',
            latitude: null,
            longitude: null,
            full_address: 'Default location'
        };
        
        locationSpinner.classList.add('d-none');
        locationMessage.innerHTML = `
            <div class="text-info">
                Using default location settings
            </div>
        `;
        
        setTimeout(() => {
            startProcessing();
        }, 1000);
    }

    // Event listeners for location buttons
    getLocationBtn.addEventListener('click', getCurrentLocation);
    skipLocationBtn.addEventListener('click', useDefaultLocation);

    // Step 4 -> Processing flow
    async function startProcessing() {
        if (!userLocation) {
            useDefaultLocation();
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
                    activity: activityInput.value.trim()
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
                    location: userLocation
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

    // Handle restart button
    restartBtn.addEventListener('click', function() {
        // Reset all inputs and variables
        nameInput.value = '';
        activityInput.value = '';
        userName = '';
        userLocation = null;
        
        // Reset location UI
        locationSpinner.classList.add('d-none');
        locationMessage.textContent = 'Click below to share your location';
        getLocationBtn.disabled = false;
        getLocationBtn.textContent = 'Share Location';
        
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