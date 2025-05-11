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
    const copyButton = document.getElementById('copyBtn');
    const phraseTableBody = document.getElementById('phraseTable');
    const errorAlert = document.getElementById('error-alert');

    // --- Function to display errors ---
    function showError(message) {
        errorAlert.textContent = message || 'An unknown error occurred.';
        errorAlert.classList.remove('d-none'); // Make visible
    }

    function hideError() {
        errorAlert.classList.add('d-none'); // Hide
        errorAlert.textContent = '';
    }

    // --- Function to load phrases into the table ---
    async function loadPhrases() {
        console.log("Loading phrases...");
        try {
            const response = await fetch('/phrases');
            if (!response.ok) {
                console.error("Failed to load phrases:", response.status, await response.text());
                phraseTableBody.innerHTML = '<tr><td colspan="3" class="text-danger">Could not load phrases.</td></tr>';
                return;
            }
            const phrases = await response.json();
            phraseTableBody.innerHTML = ''; // Clear "Loading..." message or previous entries

            if (phrases.length === 0) {
                 phraseTableBody.innerHTML = '<tr><td colspan="3">No phrases found in database.</td></tr>';
                 return;
            }

            phrases.forEach(phrase => {
                const row = phraseTableBody.insertRow();
                row.insertCell(0).textContent = phrase.SylhetiText;
                row.insertCell(1).textContent = phrase.BengaliText;
                row.insertCell(2).textContent = phrase.EnglishText;
            });
            console.log("Phrases loaded.");
        } catch (error) {
            console.error("Error loading phrases:", error);
            phraseTableBody.innerHTML = '<tr><td colspan="3" class="text-danger">Error connecting to server to load phrases.</td></tr>';
        }
    }

    // --- Function to handle translation ---
    async function handleTranslate() {
        const sourceText = sourceTextArea.value;
        const sourceLang = sourceLanguageSelect.value;
        const targetLang = targetLanguageSelect.value;

        targetTextArea.value = ''; // Clear previous translation
        hideError(); // Hide previous errors

        if (!sourceText.trim()) {
            showError('Please enter text to translate!');
            return;
        }

        if (sourceLang === targetLang) {
            showError('Source and target languages cannot be the same.');
            return;
        }

        targetTextArea.value = 'Translating...'; // Provide feedback
        translateButton.disabled = true; // Disable button during request

        console.log(`Sending to /translate: text='${sourceText}', source_lang='${sourceLang}', target_lang='${targetLang}'`);

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json' // Explicitly accept JSON
                },
                body: JSON.stringify({
                    text: sourceText,
                    source_lang: sourceLang,
                    target_lang: targetLang
                })
            });

            console.log("Response status from /translate:", response.status);

            // Try to parse JSON regardless of status code for more informative errors
            let responseData;
            try {
                 responseData = await response.json();
                 console.log("Received response data:", responseData);
            } catch (jsonError) {
                 // Handle cases where response is not valid JSON (e.g., server crash HTML page)
                 console.error("Failed to parse JSON response:", jsonError);
                 console.error("Response text:", await response.text().catch(() => "Could not get response text."));
                 showError(`Server returned non-JSON response (Status: ${response.status}). Check backend logs.`);
                 targetTextArea.value = ''; // Clear 'Translating...'
                 translateButton.disabled = false; // Re-enable button
                 return;
            }

            if (!response.ok) {
                // Handle errors reported correctly by the backend API (with JSON body)
                console.error('Translation API Error:', responseData);
                // Use the error message from the backend JSON if available
                showError(responseData.error || `Translation failed with status: ${response.status}`);
                targetTextArea.value = ''; // Clear 'Translating...'
            } else {
                // Success case
                targetTextArea.value = responseData.translation;
            }

        } catch (error) {
            // Handle network errors (e.g., server down) or fetch failures
            console.error('Fetch Error:', error);
            showError('Network Error: Could not connect to the translation server.');
            targetTextArea.value = ''; // Clear 'Translating...'
        } finally {
             translateButton.disabled = false; // Re-enable button after request finishes (success or fail)
        }
    }

    // --- Event Listeners ---
    if (translateButton) {
        translateButton.addEventListener('click', handleTranslate);
    }

    if (clearButton) {
        clearButton.addEventListener('click', () => {
            sourceTextArea.value = '';
            targetTextArea.value = '';
            hideError();
            sourceTextArea.focus();
        });
    }

     if (copyButton) {
        copyButton.addEventListener('click', () => {
            const textToCopy = targetTextArea.value;
            if (textToCopy) {
                navigator.clipboard.writeText(textToCopy)
                    .then(() => {
                        // Optional: Provide feedback like changing button text briefly
                        const originalText = copyButton.innerHTML;
                        copyButton.innerHTML = '<i class="bi bi-clipboard-check"></i> Copied!';
                        setTimeout(() => { copyButton.innerHTML = originalText; }, 1500);
                    })
                    .catch(err => {
                        console.error('Failed to copy text: ', err);
                        alert('Failed to copy translation to clipboard.'); // Fallback alert
                    });
            }
        });
    }

    // --- Initial Load ---
    loadPhrases();
});