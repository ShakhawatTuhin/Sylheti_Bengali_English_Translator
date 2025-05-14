// =======================================
// File: static/script.js
// =======================================

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const sourceLanguageSelect = document.getElementById('sourceLanguage');
    const targetLanguageSelect = document.getElementById('targetLanguage');
    const sourceTextArea = document.getElementById('sourceText');
    const targetTextArea = document.getElementById('targetText');
    const translateButton = document.getElementById('translateBtn');
    const clearButton = document.getElementById('clearBtn');
    const sourceClearButton = document.getElementById('sourceClearBtn');
    const sourceListenButton = document.getElementById('sourceListenBtn');
    const copyButton = document.getElementById('copyBtn');
    const listenButton = document.getElementById('listenBtn');
    const swapLanguagesButton = document.getElementById('swapLanguagesBtn');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const phraseTableBody = document.getElementById('phraseTable');
    const errorAlert = document.getElementById('error-alert');
    const phraseSearch = document.getElementById('phraseSearch');
    const phraseSearchBtn = document.getElementById('phraseSearchBtn');
    const translationOverlay = document.querySelector('.translation-overlay');

    // Store all phrases for search functionality
    let allPhrases = [];
    let translationTimeout = null;

    // --- Function to display errors ---
    function showError(message) {
        errorAlert.textContent = message || 'An unknown error occurred.';
        errorAlert.classList.remove('d-none');
        errorAlert.classList.add('animate__animated', 'animate__fadeIn');
        
        // Automatically hide after 5 seconds
        setTimeout(() => {
            hideError();
        }, 5000);
    }

    function hideError() {
        errorAlert.classList.add('d-none');
        errorAlert.textContent = '';
    }

    // --- Dark/Light Mode Toggle ---
    function setColorMode(isDark) {
        if (isDark) {
            document.documentElement.classList.add('dark-mode');
            document.documentElement.classList.remove('light-mode');
            localStorage.setItem('darkMode', 'enabled');
        } else {
            document.documentElement.classList.add('light-mode');
            document.documentElement.classList.remove('dark-mode');
            localStorage.setItem('darkMode', 'disabled');
        }
    }

    // Check for saved user preference
    function initColorMode() {
        const savedMode = localStorage.getItem('darkMode');
        if (savedMode === 'disabled') {
            darkModeToggle.checked = false;
            setColorMode(false);
        } else {
            darkModeToggle.checked = true;
            setColorMode(true);
        }
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', () => {
            setColorMode(darkModeToggle.checked);
        });
        
        // Initialize based on saved preference
        initColorMode();
    }

    // --- Function to load phrases into the table ---
    async function loadPhrases() {
        console.log("Loading phrases...");
        try {
            const response = await fetch('/phrases');
            if (!response.ok) {
                console.error("Failed to load phrases:", response.status, await response.text());
                phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-danger">Could not load phrases.</td></tr>';
                return;
            }
            
            allPhrases = await response.json();
            displayPhrases(allPhrases);
            
            console.log("Phrases loaded.");
        } catch (error) {
            console.error("Error loading phrases:", error);
            phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error connecting to server to load phrases.</td></tr>';
        }
    }
    
    // Function to display phrases in the table
    function displayPhrases(phrases) {
        phraseTableBody.innerHTML = ''; // Clear previous entries

        if (phrases.length === 0) {
            phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-center">No phrases found.</td></tr>';
            return;
        }

        phrases.forEach(phrase => {
            const row = document.createElement('tr');
            
            const sylCell = document.createElement('td');
            sylCell.textContent = phrase.SylhetiText;
            row.appendChild(sylCell);
            
            const benCell = document.createElement('td');
            benCell.textContent = phrase.BengaliText;
            row.appendChild(benCell);
            
            const engCell = document.createElement('td');
            engCell.textContent = phrase.EnglishText;
            row.appendChild(engCell);
            
            // Add action buttons cell
            const actionsCell = document.createElement('td');
            actionsCell.className = 'text-center';
            
            // Create "Use" button
            const useButton = document.createElement('button');
            useButton.className = 'btn btn-sm btn-outline-secondary action-btn';
            useButton.title = 'Use this phrase';
            useButton.innerHTML = '<i class="bi bi-box-arrow-up-left"></i>';
            
            // Add event listener to button
            useButton.addEventListener('click', () => {
                // Determine source language and fill textarea
                const sourceLanguage = sourceLanguageSelect.value;
                
                if (sourceLanguage === 'sylheti') {
                    sourceTextArea.value = phrase.SylhetiText;
                } else if (sourceLanguage === 'bengali') {
                    sourceTextArea.value = phrase.BengaliText;
                } else if (sourceLanguage === 'english') {
                    sourceTextArea.value = phrase.EnglishText;
                }
                
                // Scroll to translator section
                document.querySelector('.translation-card').scrollIntoView({ behavior: 'smooth' });
            });
            
            actionsCell.appendChild(useButton);
            row.appendChild(actionsCell);
            
            phraseTableBody.appendChild(row);
        });
    }
    
    // --- Search Phrases ---
    function searchPhrases(query) {
        if (!query.trim()) {
            displayPhrases(allPhrases);
            return;
        }
        
        query = query.toLowerCase();
        const filteredPhrases = allPhrases.filter(phrase => 
            phrase.SylhetiText.toLowerCase().includes(query) ||
            phrase.BengaliText.toLowerCase().includes(query) ||
            phrase.EnglishText.toLowerCase().includes(query)
        );
        
        displayPhrases(filteredPhrases);
    }
    
    if (phraseSearchBtn) {
        phraseSearchBtn.addEventListener('click', () => {
            searchPhrases(phraseSearch.value);
        });
    }
    
    if (phraseSearch) {
        phraseSearch.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                searchPhrases(phraseSearch.value);
            }
        });
    }

    // --- Live Translation with Debouncing ---
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Modify handleTranslate to accept a parameter for showing loading UI
    async function handleTranslate(showLoadingUI = true) {
        const sourceText = sourceTextArea.value;
        const sourceLang = sourceLanguageSelect.value;
        const targetLang = targetLanguageSelect.value;

        hideError(); // Hide previous errors

        if (!sourceText.trim()) {
            targetTextArea.value = '';
            return;
        }

        if (sourceLang === targetLang) {
            showError('Source and target languages cannot be the same.');
            return;
        }

        // Show loading state only if requested
        if (showLoadingUI) {
            translateButton.disabled = true;
            translateButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Translating...';
            
            if (translationOverlay) {
                translationOverlay.classList.remove('d-none');
            }
        }

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    text: sourceText,
                    source_lang: sourceLang,
                    target_lang: targetLang
                })
            });

            let responseData;
            try {
                responseData = await response.json();
            } catch (jsonError) {
                console.error("Failed to parse JSON response:", jsonError);
                showError(`Server returned non-JSON response (Status: ${response.status}). Check backend logs.`);
                return;
            }

            if (!response.ok) {
                console.error('Translation API Error:', responseData);
                showError(responseData.error || `Translation failed with status: ${response.status}`);
                return;
            }

            // Update translation with animation
            targetTextArea.value = responseData.translation;
            targetTextArea.classList.add('highlight-success');
            setTimeout(() => targetTextArea.classList.remove('highlight-success'), 1000);

        } catch (error) {
            console.error('Translation request failed:', error);
            showError('Failed to connect to translation service. Please try again.');
        } finally {
            // Reset UI only if we were showing loading state
            if (showLoadingUI) {
                translateButton.disabled = false;
                translateButton.innerHTML = '<i class="bi bi-arrow-right-short me-1"></i> Translate';
                
                if (translationOverlay) {
                    translationOverlay.classList.add('d-none');
                }
            }
        }
    }

    // Create debounced version of handleTranslate for live translation
    const debouncedTranslate = debounce(() => handleTranslate(false), 500);

    // --- Speech Recognition Setup (Dummy) ---
    let isListening = false;

    function toggleSpeechToText() {
        if (isListening) {
            // Stop listening
            isListening = false;
            sourceListenButton.innerHTML = '<i class="bi bi-mic"></i>';
            sourceListenButton.classList.remove('btn-danger');
            // Simulate stopping speech recognition
            console.log('Stopped listening');
        } else {
            // Start listening
            isListening = true;
            sourceListenButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
            sourceListenButton.classList.add('btn-danger');
            // Simulate speech recognition
            console.log('Started listening');
            setTimeout(() => {
                // Simulate receiving speech input
                sourceTextArea.value += " This is a dummy speech recognition result.";
                toggleSpeechToText(); // Stop listening
                debouncedTranslate(); // Trigger translation
            }, 2000);
        }
    }

    // --- Text to Speech Setup (Dummy) ---
    function speakText() {
        const textToSpeak = targetTextArea.value;
        if (!textToSpeak) {
            showError('No text to speak!');
            return;
        }
        
        // Simulate text-to-speech
        console.log('Speaking:', textToSpeak);
        listenButton.disabled = true;
        listenButton.innerHTML = '<i class="bi bi-volume-up-fill"></i> Speaking...';
        
        setTimeout(() => {
            listenButton.disabled = false;
            listenButton.innerHTML = '<i class="bi bi-volume-up"></i> Listen';
            console.log('Finished speaking');
        }, 2000);
    }

    // --- Event Listeners ---
    // Live translation on input
    sourceTextArea.addEventListener('input', debouncedTranslate);
    
    // Language selection changes should trigger translation
    sourceLanguageSelect.addEventListener('change', () => handleTranslate(true));
    targetLanguageSelect.addEventListener('change', () => handleTranslate(true));
    
    // Speech to text button
    sourceListenButton.addEventListener('click', toggleSpeechToText);
    
    // Text to speech button
    listenButton.addEventListener('click', speakText);

    // Original event listeners
    translateButton.addEventListener('click', () => handleTranslate(true));
    clearButton.addEventListener('click', () => {
        sourceTextArea.value = '';
        targetTextArea.value = '';
        hideError();
    });
    
    sourceClearButton.addEventListener('click', () => {
        sourceTextArea.value = '';
        targetTextArea.value = '';
        hideError();
    });

    if (copyButton) {
        copyButton.addEventListener('click', () => {
            const textToCopy = targetTextArea.value;
            if (textToCopy) {
                navigator.clipboard.writeText(textToCopy)
                    .then(() => {
                        // Provide feedback
                        const originalText = copyButton.innerHTML;
                        copyButton.innerHTML = '<i class="bi bi-clipboard-check"></i> Copied!';
                        setTimeout(() => { copyButton.innerHTML = originalText; }, 1500);
                    })
                    .catch(err => {
                        console.error('Failed to copy text: ', err);
                        showError('Failed to copy translation to clipboard.');
                    });
            }
        });
    }
    
    if (swapLanguagesButton) {
        swapLanguagesButton.addEventListener('click', swapLanguages);
    }

    // Add enter key support for translation
    sourceTextArea.addEventListener('keydown', (e) => {
        // Check if Ctrl+Enter or Cmd+Enter was pressed
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            handleTranslate();
        }
    });

    // --- Initial Load ---
    loadPhrases();
    
    // Focus on the source textarea for immediate input
    sourceTextArea.focus();
    
    // Add CSS class for stylesheet effects
    document.body.classList.add('js-enabled');

    // --- Function to swap languages ---
    function swapLanguages() {
        // Get current values
        const sourceText = sourceTextArea.value;
        const sourceLang = sourceLanguageSelect.value;
        const targetText = targetTextArea.value;
        const targetLang = targetLanguageSelect.value;
        
        // Swap languages
        sourceLanguageSelect.value = targetLang;
        targetLanguageSelect.value = sourceLang;
        
        // If we have a translation already, swap the text too
        if (targetText.trim()) {
            sourceTextArea.value = targetText;
            targetTextArea.value = sourceText;
        }
        
        // Add animation classes
        sourceLanguageSelect.classList.add('swap-animation');
        targetLanguageSelect.classList.add('swap-animation');
        
        // Remove animation classes after animation completes
        setTimeout(() => {
            sourceLanguageSelect.classList.remove('swap-animation');
            targetLanguageSelect.classList.remove('swap-animation');
        }, 500);

        // Trigger translation if needed
        if (sourceTextArea.value.trim()) {
            handleTranslate(true);
        }
    }
});