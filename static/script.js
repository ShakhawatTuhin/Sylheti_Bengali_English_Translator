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
    const historyList = document.getElementById('historyList');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const sourceCharCount = document.getElementById('sourceCharCount');
    const targetCharCount = document.getElementById('targetCharCount');

    // Store all phrases for search functionality
    let allPhrases = [];
    let translationTimeout = null;
    let translationHistory = JSON.parse(localStorage.getItem('translationHistory') || '[]');
    let isListening = false;
    let recordingStartTime;

    // --- Character Count Functions ---
    function updateCharCount(textarea, countElement) {
        const count = textarea.value.length;
        countElement.textContent = `${count} character${count !== 1 ? 's' : ''}`;
    }

    // Update character counts on input
    sourceTextArea.addEventListener('input', () => updateCharCount(sourceTextArea, sourceCharCount));
    targetTextArea.addEventListener('input', () => updateCharCount(targetTextArea, targetCharCount));

    // --- Translation History Functions ---
    function addToHistory(sourceText, targetText, sourceLang, targetLang) {
        const historyItem = {
            sourceText,
            targetText,
            sourceLang,
            targetLang,
            timestamp: new Date().toISOString()
        };

        translationHistory.unshift(historyItem); // Add to beginning
        if (translationHistory.length > 50) { // Keep only last 50 translations
            translationHistory.pop();
        }

        localStorage.setItem('translationHistory', JSON.stringify(translationHistory));
        displayHistory();
    }

    function displayHistory() {
        if (!historyList) return;

        historyList.innerHTML = '';
        if (translationHistory.length === 0) {
            historyList.innerHTML = '<div class="text-center text-secondary p-3">No translation history yet</div>';
            return;
        }

        translationHistory.forEach((item, index) => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.innerHTML = `
                <div class="languages">
                    ${item.sourceLang.toUpperCase()} → ${item.targetLang.toUpperCase()}
                </div>
                <div class="text-pair">
                    <div class="source-text">${item.sourceText}</div>
                    <div class="target-text">${item.targetText}</div>
                </div>
                <div class="timestamp">
                    ${new Date(item.timestamp).toLocaleString()}
                </div>
                <div class="actions">
                    <button class="btn btn-sm btn-outline-secondary reuse-btn">
                        <i class="bi bi-arrow-counterclockwise"></i> Reuse
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-btn">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;

            // Add event listeners for history item buttons
            const reuseBtn = historyItem.querySelector('.reuse-btn');
            const deleteBtn = historyItem.querySelector('.delete-btn');

            reuseBtn.addEventListener('click', () => {
                sourceLanguageSelect.value = item.sourceLang;
                targetLanguageSelect.value = item.targetLang;
                sourceTextArea.value = item.sourceText;
                updateCharCount(sourceTextArea, sourceCharCount);
                handleTranslate(true);
            });

            deleteBtn.addEventListener('click', () => {
                translationHistory.splice(index, 1);
                localStorage.setItem('translationHistory', JSON.stringify(translationHistory));
                displayHistory();
            });

            historyList.appendChild(historyItem);
        });
    }

    // Clear history button
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all translation history?')) {
                translationHistory = [];
                localStorage.setItem('translationHistory', JSON.stringify(translationHistory));
                displayHistory();
            }
        });
    }

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
                console.error("Failed to load phrases:", response.status);
                phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-danger">Could not load phrases.</td></tr>';
                return;
            }
            
            const data = await response.json();
            
            // Check if data is an array and has items
            if (Array.isArray(data)) {
                allPhrases = data;
                if (data.length === 0) {
                    phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-center">No phrases available in the database.</td></tr>';
                } else {
                    displayPhrases(allPhrases);
                }
            } else {
                console.error("Invalid data format received:", data);
                phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-danger">Invalid data format received from server.</td></tr>';
            }
            
        } catch (error) {
            console.error("Error loading phrases:", error);
            phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error connecting to server. Please try refreshing the page.</td></tr>';
        }
    }
    
    // Function to display phrases in the table
    function displayPhrases(phrases) {
        phraseTableBody.innerHTML = ''; // Clear previous entries

        if (!Array.isArray(phrases) || phrases.length === 0) {
            phraseTableBody.innerHTML = '<tr><td colspan="4" class="text-center">No phrases found.</td></tr>';
            return;
        }

        phrases.forEach(phrase => {
            const row = document.createElement('tr');
            
            const sylCell = document.createElement('td');
            sylCell.textContent = phrase.SylhetiText || '';
            row.appendChild(sylCell);
            
            const benCell = document.createElement('td');
            benCell.textContent = phrase.BengaliText || '';
            row.appendChild(benCell);
            
            const engCell = document.createElement('td');
            engCell.textContent = phrase.EnglishText || '';
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
                let textToUse = '';
                
                if (sourceLanguage === 'sylheti') {
                    textToUse = phrase.SylhetiText;
                } else if (sourceLanguage === 'bengali') {
                    textToUse = phrase.BengaliText;
                } else if (sourceLanguage === 'english') {
                    textToUse = phrase.EnglishText;
                }
                
                if (textToUse) {
                    sourceTextArea.value = textToUse;
                    updateCharCount(sourceTextArea, sourceCharCount);
                    handleTranslate(true);
                    // Scroll to translator section
                    document.querySelector('.translation-card').scrollIntoView({ behavior: 'smooth' });
                }
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

        hideError();

        if (!sourceText.trim()) {
            targetTextArea.value = '';
            updateCharCount(targetTextArea, targetCharCount);
            return;
        }

        if (sourceLang === targetLang) {
            showError('Source and target languages cannot be the same.');
            return;
        }

        if (showLoadingUI) {
            if (translateButton) {
                translateButton.disabled = true;
                translateButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Translating...';
            }
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

            targetTextArea.value = responseData.translation;
            updateCharCount(targetTextArea, targetCharCount);
            targetTextArea.classList.add('highlight-success');
            setTimeout(() => targetTextArea.classList.remove('highlight-success'), 1000);

            // Add to history
            addToHistory(sourceText, responseData.translation, sourceLang, targetLang);

        } catch (error) {
            console.error('Translation request failed:', error);
            showError('Failed to connect to translation service. Please try again.');
        } finally {
            if (showLoadingUI) {
                if (translateButton) {
                    translateButton.disabled = false;
                    translateButton.innerHTML = '<i class="bi bi-arrow-right-short me-1"></i> Translate';
                }
                if (translationOverlay) {
                    translationOverlay.classList.add('d-none');
                }
            }
        }
    }
    
    // Create debounced version of handleTranslate for live translation
    const debouncedTranslate = debounce(() => handleTranslate(false), 500);

    // --- Speech Recognition Setup (Real) ---
    let mediaRecorder;
    let audioChunks = [];

    // Function to handle microphone data
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            isListening = true;
            sourceListenButton.innerHTML = '<i class="bi bi-mic-fill"></i> Recording...';
            sourceListenButton.classList.add('btn-danger');
            console.log('Started recording audio...');
            recordingStartTime = Date.now();

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const duration = Date.now() - recordingStartTime;
                if (duration < 1000) { // Enforce a minimum recording time of 1 second
                    showError("Recording is too short. Please hold the button and speak for at least a second.");
                    stream.getTracks().forEach(track => track.stop());
                    return;
                }

                if (audioChunks.length === 0) {
                    console.warn("No audio data recorded.");
                    showError("No audio was recorded. Please ensure your microphone is working and you speak clearly.");
                    stream.getTracks().forEach(track => track.stop());
                    return;
                }
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' }); // Changed to webm
                sendAudioToBackend(audioBlob);
                // Stop all tracks in the stream after recording finishes
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();

        } catch (error) {
            console.error('Error accessing microphone:', error);
            showError('Microphone access denied or error: ' + error.message);
            isListening = false;
            sourceListenButton.innerHTML = '<i class="bi bi-mic"></i>';
            sourceListenButton.classList.remove('btn-danger');
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            isListening = false;
            sourceListenButton.innerHTML = '<i class="bi bi-mic"></i>';
            sourceListenButton.classList.remove('btn-danger');
            sourceTextArea.value = 'Transcribing...'; // Give immediate feedback
            console.log('Stopped recording audio.');
        }
    }

    async function sendAudioToBackend(audioBlob) {
        console.log('Sending audio to backend...', audioBlob);
        sourceTextArea.value = 'Transcribing...'; // Provide immediate feedback

        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'recording.webm'); // Changed filename extension
        formData.append('source_language', sourceLanguageSelect.value);

        try {
            const response = await fetch('/stt', {
                method: 'POST',
                body: formData,
            });

            const responseData = await response.json();

            if (!response.ok) {
                console.error('STT API Error:', responseData);
                showError(responseData.error || `Speech-to-Text failed with status: ${response.status}`);
                sourceTextArea.value = ''; // Clear transcription status on error
                return;
            }

            sourceTextArea.value = responseData.transcription;
            updateCharCount(sourceTextArea, sourceCharCount);
            debouncedTranslate(); // Trigger translation with the new transcription

        } catch (error) {
            console.error('STT request failed:', error);
            showError('Failed to connect to speech recognition service. Please try again.');
            sourceTextArea.value = ''; // Clear transcription status on error
        }
    }

    function toggleSpeechToText() {
        if (isListening) {
            stopRecording();
        } else {
            startRecording();
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

    // --- Initial Setup ---
    loadPhrases();
    displayHistory();
    updateCharCount(sourceTextArea, sourceCharCount);
    updateCharCount(targetTextArea, targetCharCount);
    sourceTextArea.focus();
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
            // Update character counts
            updateCharCount(sourceTextArea, sourceCharCount);
            updateCharCount(targetTextArea, targetCharCount);
        }
        
        // Add animation classes
        sourceLanguageSelect.classList.add('swap-animation');
        targetLanguageSelect.classList.add('swap-animation');
        
        // Remove animation classes after animation completes
        setTimeout(() => {
            sourceLanguageSelect.classList.remove('swap-animation');
            targetLanguageSelect.classList.remove('swap-animation');
        }, 500);

        // Always trigger translation if there's text
        if (sourceTextArea.value.trim()) {
            handleTranslate(true);
        }
    }
});