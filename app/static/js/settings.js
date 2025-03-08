// Initialize settings when page loads
document.addEventListener('DOMContentLoaded', async () => {
    // Load available personalities
    await loadPersonalities();
    
    // Load current settings
    const settings = await loadSettings();
    populateSettings(settings);
    
    // Set up event listeners
    setupEventListeners();
});

async function loadPersonalities() {
    try {
        const response = await fetch('/api/settings/personalities');
        if (!response.ok) throw new Error('Failed to load personalities');
        const personalities = await response.json();
        
        const select = document.getElementById('personality-select');
        select.innerHTML = '';
        
        personalities.forEach(personality => {
            const option = document.createElement('option');
            option.value = personality.name;
            option.textContent = personality.name;
            select.appendChild(option);
        });
        
        // Show/hide delete button based on selected personality
        updateDeleteButton();
    } catch (error) {
        console.error('Error loading personalities:', error);
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings/personality');
        if (!response.ok) throw new Error('Failed to load settings');
        return await response.json();
    } catch (error) {
        console.error('Error loading settings:', error);
        return null;
    }
}

function populateSettings(settings) {
    if (!settings) return;
    
    // Basic Information
    document.getElementById('assistant-name').value = settings.name;
    
    // Personality Traits
    const traits = settings.traits;
    for (const [trait, value] of Object.entries(traits)) {
        const input = document.getElementById(trait);
        const valueSpan = document.getElementById(`${trait}-value`);
        if (input && valueSpan) {
            input.value = value;
            valueSpan.textContent = value;
        }
    }
    
    // Speaking Style
    const style = settings.speaking_style;
    document.getElementById('tone').value = style.tone;
    document.getElementById('language-complexity').value = style.language_complexity;
    document.getElementById('use-emojis').checked = style.uses_emojis;
    
    const emojiFreqContainer = document.getElementById('emoji-frequency-container');
    const emojiFreqInput = document.getElementById('emoji-frequency');
    const emojiFreqValue = document.getElementById('emoji-frequency-value');
    
    if (style.uses_emojis) {
        emojiFreqContainer.style.display = 'block';
        emojiFreqInput.value = style.emoji_frequency;
        emojiFreqValue.textContent = style.emoji_frequency;
    }
    
    // Expertise Areas
    const expertiseContainer = document.getElementById('expertise-tags');
    expertiseContainer.innerHTML = '';
    settings.background_story.expertise_areas.forEach(area => {
        addExpertiseTag(area);
    });
}

function setupEventListeners() {
    // Range input listeners
    document.querySelectorAll('input[type="range"]').forEach(input => {
        input.addEventListener('input', (e) => {
            const valueSpan = document.getElementById(`${e.target.id}-value`);
            if (valueSpan) {
                valueSpan.textContent = e.target.value;
            }
        });
    });
    
    // Emoji checkbox listener
    document.getElementById('use-emojis').addEventListener('change', (e) => {
        const container = document.getElementById('emoji-frequency-container');
        container.style.display = e.target.checked ? 'block' : 'none';
    });
    
    // Enter key for adding expertise
    document.getElementById('new-expertise').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addExpertise();
        }
    });
    
    // Personality select listener
    document.getElementById('personality-select').addEventListener('change', async (e) => {
        const name = e.target.value;
        try {
            const response = await fetch(`/api/settings/personality/${name}`);
            if (!response.ok) throw new Error('Failed to load personality');
            const settings = await response.json();
            populateSettings(settings);
            updateDeleteButton();
        } catch (error) {
            console.error('Error loading personality:', error);
        }
    });
    
    // New personality button
    document.getElementById('new-personality-btn').addEventListener('click', () => {
        document.getElementById('new-personality-modal').style.display = 'block';
    });
    
    // Delete personality button
    document.getElementById('delete-personality-btn').addEventListener('click', async () => {
        const name = document.getElementById('personality-select').value;
        if (confirm(`Are you sure you want to delete the personality "${name}"?`)) {
            try {
                const response = await fetch(`/api/settings/personalities/${name}`, {
                    method: 'DELETE'
                });
                if (!response.ok) throw new Error('Failed to delete personality');
                await loadPersonalities();
            } catch (error) {
                console.error('Error deleting personality:', error);
                alert('Failed to delete personality. Please try again.');
            }
        }
    });
    
    // Modal close button
    document.querySelector('.close').addEventListener('click', closeNewPersonalityModal);
}

function updateDeleteButton() {
    const deleteBtn = document.getElementById('delete-personality-btn');
    const selectedPersonality = document.getElementById('personality-select').value;
    deleteBtn.style.display = selectedPersonality === 'default' ? 'none' : 'inline-block';
}

function closeNewPersonalityModal() {
    document.getElementById('new-personality-modal').style.display = 'none';
    document.getElementById('new-personality-name').value = '';
}

async function createNewPersonality() {
    const nameInput = document.getElementById('new-personality-name');
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Please enter a name for the new personality');
        return;
    }
    
    // Get current settings as template
    const settings = await getCurrentSettings();
    settings.name = name;
    
    try {
        const response = await fetch('/api/settings/personalities/new', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) throw new Error('Failed to create personality');
        
        // Reload personalities and close modal
        await loadPersonalities();
        closeNewPersonalityModal();
        
        // Select the new personality
        document.getElementById('personality-select').value = name;
        updateDeleteButton();
    } catch (error) {
        console.error('Error creating personality:', error);
        alert('Failed to create personality. Please try again.');
    }
}

async function getCurrentSettings() {
    return {
        name: document.getElementById('assistant-name').value,
        traits: {
            friendliness: parseFloat(document.getElementById('friendliness').value),
            formality: parseFloat(document.getElementById('formality').value),
            helpfulness: parseFloat(document.getElementById('helpfulness').value),
            creativity: parseFloat(document.getElementById('creativity').value),
            humor: parseFloat(document.getElementById('humor').value)
        },
        speaking_style: {
            tone: document.getElementById('tone').value,
            language_complexity: document.getElementById('language-complexity').value,
            uses_emojis: document.getElementById('use-emojis').checked,
            emoji_frequency: parseFloat(document.getElementById('emoji-frequency').value)
        },
        behavioral_preferences: {
            proactive_suggestions: true,
            error_handling_style: "supportive",
            technical_detail_level: "adaptive"
        },
        background_story: {
            role: "AI Assistant focused on helping with tasks and organization",
            expertise_areas: Array.from(document.querySelectorAll('.expertise-tag'))
                .map(tag => tag.textContent.trim()),
            communication_style: "Clear, friendly, and solution-oriented"
        }
    };
}

async function saveSettings() {
    const settings = await getCurrentSettings();
    
    try {
        const response = await fetch('/api/settings/personality', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) throw new Error('Failed to save settings');
        
        // Show success message
        alert('Settings saved successfully!');
        window.location.href = '/';
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Failed to save settings. Please try again.');
    }
}

function addExpertise() {
    const input = document.getElementById('new-expertise');
    const text = input.value.trim();
    
    if (text) {
        addExpertiseTag(text);
        input.value = '';
    }
}

function addExpertiseTag(text) {
    const container = document.getElementById('expertise-tags');
    const tag = document.createElement('div');
    tag.className = 'expertise-tag';
    tag.innerHTML = `
        ${text}
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(tag);
} 