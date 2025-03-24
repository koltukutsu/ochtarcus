import json
import os
import time
import asyncio
import math
from colorama import init, Fore, Style
import openai
from dotenv import load_dotenv
from pydub import AudioSegment

# Initialize colorama for colored output
init()

# Load environment variables (for OpenAI API key)
load_dotenv()

# Get OpenAI API key from environment variable
OPENAI_API_KEY = "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"
if not OPENAI_API_KEY:
    print(f"{Fore.RED}[ERROR] OPENAI_API_KEY not found in environment variables. Please set it first.{Style.RESET_ALL}")
    print("You can create a .env file with the content: OPENAI_API_KEY=your_api_key_here")
    exit(1)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Maximum file size for Whisper API (24MB to be safe)
MAX_FILE_SIZE_MB = 24
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

async def transcribe_audio_chunk(chunk_path):
    """
    Transcribe a single audio chunk using OpenAI's Whisper model.
    
    Args:
        chunk_path (str): Path to the audio chunk file
        
    Returns:
        str: The transcribed text
    """
    print(f"{Fore.YELLOW}[DEBUG] Transcribing chunk: {chunk_path}{Style.RESET_ALL}")
    
    try:
        with open(chunk_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        transcription = response.text
        print(f"{Fore.GREEN}[DEBUG] Successfully transcribed chunk ({len(transcription)} characters){Style.RESET_ALL}")
        return transcription
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Chunk transcription failed: {str(e)}{Style.RESET_ALL}")
        return ""

async def transcribe_audio(audio_file_path):
    """
    Transcribe an audio file using OpenAI's Whisper model.
    If the file is too large, it will be split into chunks.
    
    Args:
        audio_file_path (str): Path to the audio file
        
    Returns:
        str: The transcribed text
    """
    print(f"{Fore.YELLOW}[DEBUG] Starting transcription of {audio_file_path}{Style.RESET_ALL}")
    
    try:
        # Check if file exists
        if not os.path.exists(audio_file_path):
            print(f"{Fore.RED}[ERROR] File not found: {audio_file_path}{Style.RESET_ALL}")
            return None
        
        # Get file size
        file_size = os.path.getsize(audio_file_path)
        
        # If file is smaller than the limit, transcribe it directly
        if file_size <= MAX_FILE_SIZE_BYTES:
            with open(audio_file_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            transcription = response.text
            print(f"{Fore.GREEN}[DEBUG] Successfully transcribed audio ({len(transcription)} characters){Style.RESET_ALL}")
            return transcription
        
        # If file is larger than the limit, split it into chunks
        print(f"{Fore.YELLOW}[DEBUG] File size ({file_size/1024/1024:.2f} MB) exceeds limit. Splitting into chunks.{Style.RESET_ALL}")
        
        # Create a temporary directory for chunks
        temp_dir = os.path.join(os.path.dirname(audio_file_path), "temp_chunks")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Load the audio file
        audio = AudioSegment.from_file(audio_file_path)
        
        # Calculate how many chunks we need
        audio_length_ms = len(audio)
        chunk_size_ms = math.floor(audio_length_ms * (MAX_FILE_SIZE_BYTES / file_size))
        num_chunks = math.ceil(audio_length_ms / chunk_size_ms)
        
        print(f"{Fore.YELLOW}[DEBUG] Splitting audio into {num_chunks} chunks{Style.RESET_ALL}")
        
        # Split the audio into chunks and save them
        chunk_paths = []
        for i in range(num_chunks):
            start_ms = i * chunk_size_ms
            end_ms = min((i + 1) * chunk_size_ms, audio_length_ms)
            
            chunk = audio[start_ms:end_ms]
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3")
            chunk_paths.append(chunk_path)
            
            print(f"{Fore.YELLOW}[DEBUG] Created chunk {i+1}/{num_chunks}: {chunk_path}{Style.RESET_ALL}")
        
        # Transcribe all chunks asynchronously
        tasks = [transcribe_audio_chunk(chunk_path) for chunk_path in chunk_paths]
        chunk_transcriptions = await asyncio.gather(*tasks)
        
        # Combine all transcriptions
        full_transcription = " ".join(chunk_transcriptions)
        
        # Clean up temporary files
        for chunk_path in chunk_paths:
            os.remove(chunk_path)
        os.rmdir(temp_dir)
        
        print(f"{Fore.GREEN}[DEBUG] Successfully transcribed all chunks ({len(full_transcription)} characters){Style.RESET_ALL}")
        return full_transcription
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Transcription failed: {str(e)}{Style.RESET_ALL}")
        return None

async def process_item(item, i, total_items):
    """
    Process a single item from the data.
    
    Args:
        item (dict): The item to process
        i (int): The index of the item
        total_items (int): The total number of items
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{Fore.CYAN}[INFO] Processing item {i}/{total_items}: {item.get('name_video', 'Unnamed')}{Style.RESET_ALL}")
    
    # 1. Get the MP3 file path
    mp3_file = item.get('mp3_file')
    if not mp3_file:
        print(f"{Fore.YELLOW}[WARNING] No MP3 file found for item {i}, skipping{Style.RESET_ALL}")
        return False
    
    # Make sure the path is in the downloaded directory
    mp3_file = os.path.join('./downloaded', os.path.basename(mp3_file))
    
    # 2. Transcribe the MP3 using Whisper model
    transcription = await transcribe_audio(mp3_file)
    if not transcription:
        print(f"{Fore.YELLOW}[WARNING] Could not transcribe item {i}, skipping{Style.RESET_ALL}")
        return False
    
    # 3. Add transcription to the item
    item['mp3_content'] = transcription
    return True

async def process_data_async():
    """
    Asynchronous version of the main function to process the YC video data.
    """
    print(f"{Fore.CYAN}[INFO] Starting YC video transcription process{Style.RESET_ALL}")
    
    # 0. Load the data from video-data-updated.json instead of yc-video-data-downloaded.json
    try:
        with open('video-data-updated.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"{Fore.GREEN}[INFO] Loaded data with {len(data)} items{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to load data: {str(e)}{Style.RESET_ALL}")
        return
    
    # Track the number of successfully transcribed items
    success_count = 0
    
    # Start from the 110th item (index 109)
    start_index = 109
    print(f"{Fore.CYAN}[INFO] Starting from item {start_index + 1} (110th item) out of {len(data)} items{Style.RESET_ALL}")
    
    # Process each item in the data, starting from the 110th item
    for i, item in enumerate(data[start_index:], start_index + 1):
        success = await process_item(item, i, len(data))
        if success:
            success_count += 1
            
            # Save the updated data to video-data-updated-2.json after each successful transcription
            try:
                with open('./video-data-updated-2.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"{Fore.GREEN}[INFO] Saved updated data after processing item {i}/{len(data)}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}[INFO] {success_count} items transcribed, {len(data) - (i - start_index)} items remaining{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}[ERROR] Failed to save data: {str(e)}{Style.RESET_ALL}")
    
    # 5. Print finalization message
    print(f"\n{Fore.GREEN}[INFO] === FINALIZED ===={Style.RESET_ALL}")
    print(f"{Fore.GREEN}[INFO] Successfully transcribed {success_count} out of {len(data) - start_index} items processed{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[INFO] Results saved to ./video-data-updated-2.json{Style.RESET_ALL}")

def process_data():
    """
    Main function to process the YC video data.
    """
    asyncio.run(process_data_async())

if __name__ == "__main__":
    process_data()