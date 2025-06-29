// Map functionality for WhatNowAI
class EventsMap {
    constructor() {
        this.map = null;
        this.markers = [];
        this.allEvents = [];
        this.filteredEvents = [];
        this.activeFilters = new Set(['all']);
        this.userLocation = null;
        
        this.init();
    }
    
    init() {
        this.initializeMap();
        this.bindEvents();
        this.loadEvents();
    }
    
    initializeMap() {
        // Initialize Leaflet map
        this.map = L.map('map').setView([37.7749, -122.4194], 12); // Default to SF
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);
        
        // Get user location if available
        let userData = window.userData || {};
        
        // Try to get data from sessionStorage if not available in window
        if (!userData.location && sessionStorage.getItem('userData')) {
            try {
                userData = JSON.parse(sessionStorage.getItem('userData'));
                window.userData = userData; // Update window object
                console.log('Loaded user data from sessionStorage:', userData);
            } catch (e) {
                console.error('Error parsing user data from sessionStorage:', e);
            }
        }
        
        console.log('Final userData in initializeMap:', userData);
        console.log('Location data check:', userData.location);
        
        if (userData && userData.location) {
            const location = userData.location;
            console.log('Location object:', location);
            console.log('Latitude:', location.latitude, 'Type:', typeof location.latitude);
            console.log('Longitude:', location.longitude, 'Type:', typeof location.longitude);
            
            if (location.latitude && location.longitude) {
                this.userLocation = [location.latitude, location.longitude];
                this.map.setView(this.userLocation, 12);
                
                // Add user location marker
                this.addUserLocationMarker(location.latitude, location.longitude);
            }
        }
    }
    
    addUserLocationMarker(lat, lng) {
        const userIcon = L.divIcon({
            className: 'user-location-marker',
            html: '<i class="fas fa-user"></i>',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        L.marker([lat, lng], { icon: userIcon })
            .addTo(this.map)
            .bindPopup('<strong>Your Location</strong>')
            .openPopup();
    }
    
    bindEvents() {
        // Search functionality
        document.getElementById('search-btn').addEventListener('click', () => {
            this.searchEvents();
        });
        
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchEvents();
            }
        });
        
        // Map controls
        document.getElementById('locate-btn').addEventListener('click', () => {
            this.centerOnUserLocation();
        });
        
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.refreshEvents();
        });
    }
    
    async loadEvents() {
        const loadingIndicator = document.getElementById('loading-indicator');
        loadingIndicator.style.display = 'block';
        
        // Ensure we have user data
        let userData = window.userData || {};
        
        // Try to get data from sessionStorage if not available in window
        if (!userData.location && sessionStorage.getItem('userData')) {
            try {
                userData = JSON.parse(sessionStorage.getItem('userData'));
                window.userData = userData; // Update window object
                console.log('Loaded user data from sessionStorage:', userData);
            } catch (e) {
                console.error('Error parsing user data from sessionStorage:', e);
            }
        }
        
        console.log('User data for events request:', userData);
        console.log('loadEvents called');
        console.log('window.userData:', window.userData);
        console.log('Location data:', userData.location);
        
        // If we still don't have location data, try to get user's current location
        if (!userData.location || !userData.location.latitude || !userData.location.longitude) {
            console.log('No location data found, attempting to get current location...');
            console.log('userData.location exists:', !!userData.location);
            if (userData.location) {
                console.log('latitude exists:', !!userData.location.latitude);
                console.log('longitude exists:', !!userData.location.longitude);
                console.log('latitude value:', userData.location.latitude);
                console.log('longitude value:', userData.location.longitude);
            }
            await this.tryGetCurrentLocation(userData);
        }
        
        console.log('About to send request with location:', userData.location);
        
        try {
            const response = await fetch('/map/events', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    location: userData.location || {},
                    interests: this.extractInterests(),
                    activity: userData.activity || '',
                    personalization_data: userData.personalization_data || {}  // Include personalization data
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.allEvents = data.map_data.markers || [];
                this.filteredEvents = [...this.allEvents];
                
                this.displayEvents();
                this.displayCategoryFilters(data.category_stats || {});
                this.addMarkersToMap();
                
                // Log personalization info
                if (data.personalization_applied) {
                    console.log(`✅ Personalization applied with ${data.personalization_score}% score`);
                } else {
                    console.log('⚠️ Basic event filtering applied (no personalization data)');
                }
            } else {
                this.showError(data.message || 'Failed to load events');
            }
            
        } catch (error) {
            console.error('Error loading events:', error);
            this.showError('Failed to load events. Please try again.');
        } finally {
            loadingIndicator.style.display = 'none';
        }
    }
    
    async tryGetCurrentLocation(userData) {
        return new Promise((resolve) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        
                        console.log(`Got current location: ${lat}, ${lon}`);
                        
                        // Update user data with current location
                        userData.location = {
                            latitude: lat,
                            longitude: lon,
                            city: 'Current Location',
                            country: ''
                        };
                        
                        // Update window and sessionStorage
                        window.userData = userData;
                        sessionStorage.setItem('userData', JSON.stringify(userData));
                        
                        // Update map view
                        this.userLocation = [lat, lon];
                        this.map.setView(this.userLocation, 12);
                        this.addUserLocationMarker(lat, lon);
                        
                        resolve();
                    },
                    (error) => {
                        console.warn('Geolocation failed:', error);
                        // Use default location (San Francisco)
                        userData.location = {
                            latitude: 37.7749,
                            longitude: -122.4194,
                            city: 'San Francisco',
                            country: 'US'
                        };
                        window.userData = userData;
                        resolve();
                    },
                    { timeout: 10000, enableHighAccuracy: true }
                );
            } else {
                console.warn('Geolocation not supported');
                // Use default location
                userData.location = {
                    latitude: 37.7749,
                    longitude: -122.4194,
                    city: 'San Francisco',
                    country: 'US'
                };
                window.userData = userData;
                resolve();
            }
        });
    }
    
    extractInterests() {
        // Extract interests from user's activity, social data, and personalization data
        const interests = [];
        const activity = window.userData.activity || '';
        const personalizationData = window.userData.personalization_data || {};
        
        // Simple keyword mapping to interests
        const keywordMap = {
            'music': ['music', 'concert', 'band', 'song', 'album', 'artist', 'festival', 'show', 'performance'],
            'sports': ['sport', 'game', 'team', 'fitness', 'exercise', 'basketball', 'football', 'soccer', 'tennis', 'golf'],
            'arts': ['art', 'theater', 'museum', 'gallery', 'dance', 'exhibition', 'culture', 'painting', 'sculpture'],
            'food': ['food', 'restaurant', 'cooking', 'cuisine', 'chef', 'dining', 'culinary', 'recipe', 'meal'],
            'technology': ['tech', 'programming', 'code', 'software', 'computer', 'digital', 'innovation', 'startup'],
            'entertainment': ['movie', 'film', 'tv', 'show', 'entertainment', 'comedy', 'drama', 'cinema'],
            'nature': ['nature', 'outdoor', 'hiking', 'camping', 'park', 'beach', 'environment', 'eco'],
            'social': ['community', 'social', 'networking', 'meetup', 'group', 'volunteer', 'charity'],
            'education': ['education', 'learning', 'workshop', 'seminar', 'course', 'training', 'lecture'],
            'business': ['business', 'networking', 'entrepreneur', 'startup', 'conference', 'professional']
        };
        
        // Extract from activity description
        const activityLower = activity.toLowerCase();
        for (const [interest, keywords] of Object.entries(keywordMap)) {
            if (keywords.some(keyword => activityLower.includes(keyword))) {
                interests.push(interest);
            }
        }
        
        // Extract from personalization data search summaries
        if (personalizationData.search_summaries) {
            for (const [source, summary] of Object.entries(personalizationData.search_summaries)) {
                if (summary && typeof summary === 'string') {
                    const summaryLower = summary.toLowerCase();
                    for (const [interest, keywords] of Object.entries(keywordMap)) {
                        if (keywords.some(keyword => summaryLower.includes(keyword))) {
                            if (!interests.includes(interest)) {
                                interests.push(interest);
                            }
                        }
                    }
                }
            }
        }
        
        // If personalization data has extracted interests, include them
        if (personalizationData.interests && Array.isArray(personalizationData.interests)) {
            personalizationData.interests.forEach(interestObj => {
                if (interestObj.category && !interests.includes(interestObj.category)) {
                    interests.push(interestObj.category);
                }
            });
        }
        
        console.log('Extracted interests:', interests);
        return interests;
    }
    
    displayEvents() {
        const container = document.getElementById('events-container');
        container.innerHTML = '';
        
        if (this.filteredEvents.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No events found matching your criteria.</p>';
            return;
        }
        
        this.filteredEvents.forEach(event => {
            const eventElement = this.createEventElement(event);
            container.appendChild(eventElement);
        });
    }
    
    createEventElement(event) {
        const div = document.createElement('div');
        div.className = 'event-item';
        div.dataset.eventId = event.id;
        
        // Don't show price information as requested
        const price = 'Free';
        
        div.innerHTML = `
            <div class="event-title">${event.name}</div>
            <div class="event-meta">
                <i class="fas fa-calendar"></i> ${event.date} ${event.time}
            </div>
            <div class="event-meta">
                <i class="fas fa-map-marker-alt"></i> ${event.venue}
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <span class="event-category ${event.category}">${event.category}</span>
                <small class="text-muted">${price}</small>
            </div>
        `;
        
        div.addEventListener('click', () => {
            this.showEventDetails(event);
            this.highlightEventMarker(event.id);
        });
        
        return div;
    }
    
    displayCategoryFilters(categoryStats) {
        const container = document.getElementById('category-filters');
        container.innerHTML = '';
        
        // Add "All" filter
        const allButton = this.createFilterButton('all', 'All Events', this.allEvents.length);
        container.appendChild(allButton);
        
        // Add category filters
        Object.entries(categoryStats).forEach(([category, count]) => {
            const button = this.createFilterButton(category, category, count);
            container.appendChild(button);
        });
    }
    
    createFilterButton(category, label, count) {
        const button = document.createElement('button');
        button.className = `btn category-filter w-100 ${this.activeFilters.has(category) ? 'active' : ''}`;
        button.dataset.category = category;
        
        button.innerHTML = `
            ${label.charAt(0).toUpperCase() + label.slice(1)}
            <span class="badge">${count}</span>
        `;
        
        button.addEventListener('click', () => {
            this.toggleFilter(category);
        });
        
        return button;
    }
    
    toggleFilter(category) {
        if (category === 'all') {
            this.activeFilters.clear();
            this.activeFilters.add('all');
            this.filteredEvents = [...this.allEvents];
        } else {
            this.activeFilters.delete('all');
            
            if (this.activeFilters.has(category)) {
                this.activeFilters.delete(category);
            } else {
                this.activeFilters.add(category);
            }
            
            if (this.activeFilters.size === 0) {
                this.activeFilters.add('all');
                this.filteredEvents = [...this.allEvents];
            } else {
                this.filteredEvents = this.allEvents.filter(event => 
                    this.activeFilters.has(event.category)
                );
            }
        }
        
        this.updateFilterButtons();
        this.displayEvents();
        this.updateMapMarkers();
    }
    
    updateFilterButtons() {
        const buttons = document.querySelectorAll('.category-filter');
        buttons.forEach(button => {
            const category = button.dataset.category;
            button.classList.toggle('active', this.activeFilters.has(category));
        });
    }
    
    addMarkersToMap() {
        // Clear existing markers
        this.clearMarkers();
        
        // Add markers for all events
        this.allEvents.forEach(event => {
            const marker = this.createEventMarker(event);
            this.markers.push(marker);
        });
        
        this.updateMapMarkers();
    }
    
    createEventMarker(event) {
        const icon = L.divIcon({
            className: `custom-marker ${event.category}`,
            html: this.getCategoryIcon(event.category),
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        });
        
        const marker = L.marker([event.latitude, event.longitude], { icon: icon });
        marker.eventData = event;
        
        // Create popup content
        const popupContent = this.createPopupContent(event);
        marker.bindPopup(popupContent);
        
        // Add click event
        marker.on('click', () => {
            this.showEventDetails(event);
        });
        
        return marker;
    }
    
    getCategoryIcon(category) {
        const icons = {
            'music': '<i class="fas fa-music"></i>',
            'sports': '<i class="fas fa-football-ball"></i>',
            'arts': '<i class="fas fa-palette"></i>',
            'family': '<i class="fas fa-users"></i>',
            'miscellaneous': '<i class="fas fa-calendar"></i>'
        };
        
        return icons[category] || icons['miscellaneous'];
    }
    
    createPopupContent(event) {
        // Don't show price information as requested
        const price = 'Free';
        
        return `
            <div class="popup-content">
                <div class="popup-title">${event.name}</div>
                <div class="popup-meta">
                    <i class="fas fa-calendar"></i> ${event.date} ${event.time}<br>
                    <i class="fas fa-map-marker-alt"></i> ${event.venue}<br>
                    <i class="fas fa-tag"></i> ${price}
                </div>
                <span class="popup-category ${event.category}">${event.category}</span>
                <div class="popup-actions">
                    <a href="#" class="popup-btn popup-btn-secondary" onclick="eventsMap.showEventDetails('${event.id}'); return false;">Details</a>
                    ${event.url ? `<a href="${event.url}" class="popup-btn popup-btn-primary" target="_blank">View Event</a>` : ''}
                </div>
            </div>
        `;
    }
    
    updateMapMarkers() {
        // Remove all markers from map
        this.markers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        
        // Add filtered markers to map
        this.markers.forEach(marker => {
            const event = marker.eventData;
            if (this.activeFilters.has('all') || this.activeFilters.has(event.category)) {
                marker.addTo(this.map);
            }
        });
    }
    
    clearMarkers() {
        this.markers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers = [];
    }
    
    showEventDetails(eventOrId) {
        let event;
        if (typeof eventOrId === 'string') {
            event = this.allEvents.find(e => e.id === eventOrId);
        } else {
            event = eventOrId;
        }
        
        if (!event) return;
        
        const modal = new bootstrap.Modal(document.getElementById('event-modal'));
        
        // Populate modal content
        document.getElementById('event-title').textContent = event.name;
        
        // Don't show price information as requested
        const price = '<span class="event-price">Free</span>';
        
        document.getElementById('event-details').innerHTML = `
            ${event.image_url ? `<img src="${event.image_url}" alt="${event.name}" class="event-image">` : ''}
            <div class="event-info-grid">
                <div class="event-info-item">
                    <i class="fas fa-calendar"></i>
                    <span>${event.date} at ${event.time}</span>
                </div>
                <div class="event-info-item">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${event.venue}</span>
                </div>
                <div class="event-info-item">
                    <i class="fas fa-home"></i>
                    <span>${event.address}</span>
                </div>
                <div class="event-info-item">
                    <i class="fas fa-tag"></i>
                    ${price}
                </div>
                <div class="event-info-item">
                    <i class="fas fa-list"></i>
                    <span class="event-category ${event.category}">${event.category}</span>
                </div>
                <div class="event-info-item">
                    <i class="fas fa-globe"></i>
                    <span>${event.source}</span>
                </div>
            </div>
            ${event.description ? `<p><strong>Description:</strong> ${event.description}</p>` : ''}
            ${event.recommendation_reason ? `<p><strong>Why this event:</strong> ${event.recommendation_reason}</p>` : ''}
        `;
        
        // Update event link
        const eventLink = document.getElementById('event-link');
        if (event.url) {
            eventLink.href = event.url;
            eventLink.style.display = 'inline-block';
        } else {
            eventLink.style.display = 'none';
        }
        
        modal.show();
    }
    
    highlightEventMarker(eventId) {
        // Find and highlight the marker
        this.markers.forEach(marker => {
            if (marker.eventData.id === eventId) {
                marker.openPopup();
                this.map.setView([marker.eventData.latitude, marker.eventData.longitude], 15);
            }
        });
        
        // Highlight event in list
        document.querySelectorAll('.event-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const eventElement = document.querySelector(`[data-event-id="${eventId}"]`);
        if (eventElement) {
            eventElement.classList.add('active');
        }
    }
    
    async searchEvents() {
        const query = document.getElementById('search-input').value.trim();
        
        if (!query) {
            this.filteredEvents = [...this.allEvents];
            this.displayEvents();
            this.updateMapMarkers();
            return;
        }
        
        try {
            const response = await fetch('/map/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.filteredEvents = data.markers || [];
                this.displayEvents();
                this.updateMapMarkers();
            } else {
                this.showError(data.message || 'Search failed');
            }
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed. Please try again.');
        }
    }
    
    centerOnUserLocation() {
        if (this.userLocation) {
            this.map.setView(this.userLocation, 14);
        } else if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    this.userLocation = [lat, lng];
                    this.map.setView(this.userLocation, 14);
                    this.addUserLocationMarker(lat, lng);
                },
                (error) => {
                    this.showError('Unable to get your location');
                }
            );
        } else {
            this.showError('Geolocation is not supported by this browser');
        }
    }
    
    refreshEvents() {
        this.loadEvents();
    }
    
    showError(message) {
        // Simple error display - you can enhance this
        alert(message);
    }
}

// Initialize the map when the page loads
let eventsMap;
document.addEventListener('DOMContentLoaded', () => {
    eventsMap = new EventsMap();
});