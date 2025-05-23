import os
from openai import OpenAI

# python-dotenv should load .env in a higher level module like database.py or main.py
# Ensure OPENAI_API_KEY is set in the environment.

api_key = os.environ.get("OPENAI_API_KEY")
client = None

if not api_key:
    print("WARNING: OPENAI_API_KEY environment variable not set. OpenAI features will be disabled.")
else:
    try:
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully.")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}. OpenAI features will be disabled.")
        client = None # Ensure client is None if initialization fails

def get_openai_client():
    """Returns the initialized OpenAI client. 
    Returns None if the client failed to initialize or API key is missing.
    """
    return client

async def get_simple_chat_completion(user_prompt: str, system_prompt: str = "You are a helpful assistant.", model="gpt-3.5-turbo"):
    """Gets a basic chat completion from OpenAI."""
    current_client = get_openai_client()
    if not current_client:
        # Fallback or error message if OpenAI client is not available
        return "OpenAI client is not initialized. Please set the OPENAI_API_KEY environment variable."

    try:
        response = current_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during OpenAI chat completion: {e}")
        # Consider how to handle this error in the application
        # For now, returning an error message string
        return f"Error communicating with OpenAI: {str(e)}"

# Placeholder for Whisper transcription
async def transcribe_audio_with_whisper(audio_file_path: str, model="whisper-1"):
    current_client = get_openai_client()
    if not current_client:
        return "OpenAI client is not initialized."
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = current_client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error during Whisper transcription: {e}")
        return f"Error transcribing audio: {str(e)}"

# Add other OpenAI related functions (e.g., for embeddings) here as needed 