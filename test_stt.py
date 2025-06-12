import requests
import os

# Define the STT endpoint URL
STT_URL = "http://127.0.0.1:5000/stt"

# Define the path to your audio file
AUDIO_FILE_PATH = "E:\A Studies\Semester 6\Project Work 2\Audio/test 1.mp3" # <--- IMPORTANT: Change this to your actual audio file path

def test_stt_endpoint():
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"Error: Audio file not found at {AUDIO_FILE_PATH}")
        print("Please create or place an audio file (e.g., test_audio.wav) in this directory.")
        return

    print(f"Attempting to send {AUDIO_FILE_PATH} to {STT_URL}")
    try:
        with open(AUDIO_FILE_PATH, 'rb') as f:
            files = {'audio_file': (os.path.basename(AUDIO_FILE_PATH), f, 'audio/wav')} # Adjust 'audio/wav' if your file is mp3 (e.g., 'audio/mpeg')
            response = requests.post(STT_URL, files=files)

        print(f"Status Code: {response.status_code}")
        print(f"Response JSON: {response.json()}")

        if response.status_code == 200:
            print("STT successful!")
            print(f"Transcription: {response.json().get('transcription')}")
        else:
            print("STT failed.")
            print(f"Error: {response.json().get('error', 'Unknown error')}")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the Flask server at {STT_URL}.")
        print("Please ensure your Flask application is running.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_stt_endpoint()
