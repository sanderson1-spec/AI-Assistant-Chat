// Initialize settings when page loads
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // First check if all required elements exist
        const requiredElements = [
            'active-character',
            'character-list-container',
            'new-character-btn',
            'character-form',
            'char-name',
            'char-description',
            'char-definition',
            'sample-messages-container',
            'add-sample-message',
            'learns-from-conversation',
            'remembers-context',
            'uses-memories',
            'delete-character'
        ];
        
        const missingElements = requiredElements.filter(id => !document.getElementById(id));
        if (missingElements.length > 0) {
            throw new Error(`Missing required elements: ${missingElements.join(', ')}`);
        }
        
        // Load available characters
        await loadCharacters();
        
        // Set up event listeners
        setupEventListeners();
        
        // Load active character if one was previously selected
        const activeCharacterName = localStorage.getItem('activeCharacter');
        if (activeCharacterName) {
            const select = document.getElementById('active-character');
            if (select) {
                select.value = activeCharacterName;
                // Trigger change event to load character details
                select.dispatchEvent(new Event('change'));
            }
        }
    } catch (error) {
        console.error('Error initializing settings:', error);
        showMessage('Error loading settings: ' + error.message, 'error');
    }
});

async function loadCharacters() {
    try {
        const response = await fetch('/api/characters');
        if (!response.ok) throw new Error('Failed to load characters');
        const characters = await response.json();
        
        // Update character cards
        const container = document.getElementById('character-list-container');
        if (!container) {
            throw new Error('Character list container not found');
        }
        
        container.innerHTML = '';
        characters.forEach(character => {
            const card = createCharacterCard(character);
            container.appendChild(card);
        });
        
        // Update character selector dropdown
        const select = document.getElementById('active-character');
        if (!select) {
            throw new Error('Character selector not found');
        }
        
        // Keep the first "Select a character..." option
        select.innerHTML = '<option value="">Select a character...</option>';
        characters.forEach(character => {
            const option = document.createElement('option');
            option.value = character.name;
            option.textContent = character.name;
            select.appendChild(option);
        });
        
        // If there's an active character, select it
        const activeCharacter = localStorage.getItem('activeCharacter');
        if (activeCharacter) {
            select.value = activeCharacter;
        }
    } catch (error) {
        console.error('Error loading characters:', error);
        throw error;
    }
}

function createCharacterCard(character) {
    const card = document.createElement('div');
    card.className = 'character-card';
    if (character.name === localStorage.getItem('activeCharacter')) {
        card.classList.add('selected');
    }
    
    card.innerHTML = `
        <h3>${character.name}</h3>
        <p>${character.description || ''}</p>
    `;
    
    card.addEventListener('click', () => loadCharacterDetails(character));
    return card;
}

async function loadCharacterDetails(character) {
    try {
        // Get all required elements
        const elements = {
            name: document.getElementById('char-name'),
            description: document.getElementById('char-description'),
            definition: document.getElementById('char-definition'),
            messagesContainer: document.getElementById('sample-messages-container'),
            learnsFromConversation: document.getElementById('learns-from-conversation'),
            remembersContext: document.getElementById('remembers-context'),
            usesMemories: document.getElementById('uses-memories'),
            deleteButton: document.getElementById('delete-character'),
            activeCharacter: document.getElementById('active-character')
        };
        
        // Check if any elements are missing
        const missingElements = Object.entries(elements)
            .filter(([_, element]) => !element)
            .map(([name, _]) => name);
            
        if (missingElements.length > 0) {
            throw new Error(`Missing required elements: ${missingElements.join(', ')}`);
        }
        
        // Update form with character details
        elements.name.value = character.name;
        elements.description.value = character.description || '';
        elements.definition.value = character.definition || '';
        
        // Load sample messages
        elements.messagesContainer.innerHTML = '';
        if (character.sample_messages) {
            character.sample_messages.forEach(message => {
                addSampleMessageField(message);
            });
        }
        
        // Update behavioral settings
        elements.learnsFromConversation.checked = character.behavioral_settings?.learns_from_conversation || false;
        elements.remembersContext.checked = character.behavioral_settings?.remembers_context || false;
        elements.usesMemories.checked = character.behavioral_settings?.uses_memories || false;
        
        // Show delete button
        elements.deleteButton.style.display = 'block';
        
        // Mark card as selected
        document.querySelectorAll('.character-card').forEach(card => {
            card.classList.remove('selected');
            if (card.querySelector('h3').textContent === character.name) {
                card.classList.add('selected');
            }
        });
        
        // Update active character selector
        elements.activeCharacter.value = character.name;
        
    } catch (error) {
        console.error('Error loading character details:', error);
        showMessage('Error loading character details: ' + error.message, 'error');
    }
}

function setupEventListeners() {
    try {
        // Active character selector
        const activeCharacterSelect = document.getElementById('active-character');
        if (!activeCharacterSelect) {
            throw new Error('Active character selector not found');
        }
        
        activeCharacterSelect.addEventListener('change', async (e) => {
            const selectedName = e.target.value;
            localStorage.setItem('activeCharacter', selectedName);
            
            // Update card selection
            document.querySelectorAll('.character-card').forEach(card => {
                card.classList.toggle('selected', 
                    card.querySelector('h3').textContent === selectedName);
            });
            
            // If a character is selected, load their details
            if (selectedName) {
                try {
                    const response = await fetch(`/api/characters/${encodeURIComponent(selectedName)}`);
                    if (!response.ok) throw new Error('Failed to load character');
                    const character = await response.json();
                    loadCharacterDetails(character);
                } catch (error) {
                    console.error('Error loading character details:', error);
                    showMessage('Error loading character details: ' + error.message, 'error');
                }
            } else {
                // If no character selected, reset the form
                resetForm();
            }
            
            // Notify the server about the active character change
            try {
                await fetch('/api/active-character', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name: selectedName })
                });
            } catch (error) {
                console.error('Error updating active character:', error);
                showMessage('Error updating active character: ' + error.message, 'error');
            }
        });
        
        // New character button
        const newCharacterBtn = document.getElementById('new-character-btn');
        if (!newCharacterBtn) {
            throw new Error('New character button not found');
        }
        
        newCharacterBtn.addEventListener('click', () => {
            resetForm();
            // Clear active character selection when creating new
            activeCharacterSelect.value = '';
        });
        
        // Add sample message button
        const addSampleMessageBtn = document.getElementById('add-sample-message');
        if (!addSampleMessageBtn) {
            throw new Error('Add sample message button not found');
        }
        
        addSampleMessageBtn.addEventListener('click', () => {
            addSampleMessageField();
        });
        
        // Form submission
        const characterForm = document.getElementById('character-form');
        if (!characterForm) {
            throw new Error('Character form not found');
        }
        
        characterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveCharacter();
        });
        
        // Delete character button
        const deleteCharacterBtn = document.getElementById('delete-character');
        if (!deleteCharacterBtn) {
            throw new Error('Delete character button not found');
        }
        
        deleteCharacterBtn.addEventListener('click', async () => {
            const nameInput = document.getElementById('char-name');
            if (!nameInput) {
                showMessage('Error: Character name field not found', 'error');
                return;
            }
            
            const name = nameInput.value;
            if (confirm(`Are you sure you want to delete the character "${name}"?`)) {
                await deleteCharacter(name);
            }
        });
    } catch (error) {
        console.error('Error setting up event listeners:', error);
        showMessage('Error setting up page: ' + error.message, 'error');
    }
}

function addSampleMessageField(message = '') {
    const container = document.getElementById('sample-messages-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'sample-message';
    messageDiv.innerHTML = `
        <textarea placeholder="Enter a sample message...">${message}</textarea>
        <button type="button" class="remove-message">&times;</button>
    `;
    
    messageDiv.querySelector('.remove-message').addEventListener('click', () => {
        messageDiv.remove();
    });
    
    container.appendChild(messageDiv);
}

function resetForm() {
    document.getElementById('char-name').value = '';
    document.getElementById('char-description').value = '';
    document.getElementById('char-definition').value = '';
    document.getElementById('sample-messages-container').innerHTML = '';
    document.getElementById('learns-from-conversation').checked = false;
    document.getElementById('remembers-context').checked = false;
    document.getElementById('uses-memories').checked = false;
    document.getElementById('delete-character').style.display = 'none';
    
    // Clear selected state from all cards
    document.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('selected');
    });
}

async function getCurrentCharacter() {
    return {
        name: document.getElementById('char-name').value,
        description: document.getElementById('char-description').value,
        definition: document.getElementById('char-definition').value,
        sample_messages: Array.from(document.querySelectorAll('.sample-message textarea'))
            .map(textarea => textarea.value)
            .filter(message => message.trim() !== ''),
        behavioral_settings: {
            learns_from_conversation: document.getElementById('learns-from-conversation').checked,
            remembers_context: document.getElementById('remembers-context').checked,
            uses_memories: document.getElementById('uses-memories').checked
        }
    };
}

async function saveCharacter() {
    const character = await getCurrentCharacter();
    console.log('Saving character:', character);
    
    try {
        console.log('Sending POST request to /api/characters');
        const response = await fetch('/api/characters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(character)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server response not OK:', response.status, errorText);
            throw new Error(`Failed to save character: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Character saved successfully:', result);
        
        // Refresh the character list
        await loadCharacters();
        
        // Show success message
        showMessage('Character saved successfully!', 'success');
        
    } catch (error) {
        console.error('Error saving character:', error);
        showMessage(`Failed to save character: ${error.message}`, 'error');
    }
}

async function deleteCharacter(name) {
    try {
        const response = await fetch(`/api/characters/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete character');
        
        // If this was the active character, clear it
        if (localStorage.getItem('activeCharacter') === name) {
            localStorage.removeItem('activeCharacter');
            // Notify server about character deactivation
            await fetch('/api/active-character', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: null })
            });
        }
        
        // Reset form and reload characters
        resetForm();
        await loadCharacters();
        
        // Show success message
        alert('Character deleted successfully!');
    } catch (error) {
        console.error('Error deleting character:', error);
        alert('Failed to delete character. Please try again.');
    }
}

function showMessage(message, type = 'info') {
    // Create message container if it doesn't exist
    let container = document.querySelector('.message-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'message-container';
        document.body.appendChild(container);
    }
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `
        ${message}
        <button type="button" class="close-message">&times;</button>
    `;
    
    // Add close button handler
    messageDiv.querySelector('.close-message').addEventListener('click', () => {
        messageDiv.remove();
    });
    
    // Add to container
    container.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
} 