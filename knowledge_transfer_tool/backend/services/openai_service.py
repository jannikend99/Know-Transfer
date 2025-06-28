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

# Whisper transcription with improved error handling
async def transcribe_audio_with_whisper(audio_file_path: str, model="whisper-1"):
    current_client = get_openai_client()
    if not current_client:
        return "OpenAI client is not initialized."
    
    # Check if file exists and has content
    if not os.path.exists(audio_file_path):
        return "Error: Audio file not found."
    
    file_size = os.path.getsize(audio_file_path)
    if file_size == 0:
        return "Error: Audio file is empty."
    
    if file_size > 25 * 1024 * 1024:  # 25MB limit for Whisper
        return "Error: Audio file is too large (maximum 25MB)."
    
    try:
        import asyncio
        
        # Get file extension to provide better error messages
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        print(f"Transcribing audio file: {audio_file_path} (size: {file_size} bytes, type: {file_ext})")
        
        # Add timeout protection for transcription API call
        timeout_seconds = 60  # Whisper can take longer, so allow up to 60 seconds
        
        def sync_transcribe():
            with open(audio_file_path, "rb") as audio_file:
                return current_client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format="text"
                )
        
        # Run the synchronous transcription with timeout
        transcript = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, sync_transcribe),
            timeout=timeout_seconds
        )
        return transcript
        
    except asyncio.TimeoutError:
        print(f"Timeout error: Audio transcription took longer than 60 seconds")
        return "Error: Audio transcription timed out. Please try with a shorter audio file."
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error during Whisper transcription: {e}")
        
        # Provide more helpful error messages based on the error type
        if "file format" in error_msg.lower() or "unsupported" in error_msg.lower():
            supported_formats = "mp3, mp4, mpeg, mpga, m4a, wav, webm"
            return f"Error: Unsupported audio format. Please use one of: {supported_formats}"
        elif "file too large" in error_msg.lower():
            return "Error: Audio file is too large. Please record a shorter message."
        elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
            return "Error: OpenAI API quota exceeded. Please check your account."
        else:
            return f"Error transcribing audio: {error_msg}"

# Add other OpenAI related functions (e.g., for embeddings) here as needed 