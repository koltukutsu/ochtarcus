import json
import os
import time
import asyncio
import math
from colorama import init, Fore, Style
from deepgram import Deepgram
from dotenv import load_dotenv
from pydub import AudioSegment

# Initialize colorama for colored output
init()

# Load environment variables
load_dotenv()

# Get Deepgram API key from environment variable
DEEPGRAM_API_KEY = "7538c71fe71db5aa67296cd1902e373e4ea5319c"
if not DEEPGRAM_API_KEY:
    print(f"{Fore.RED}[ERROR] DEEPGRAM_API_KEY not found in environment variables. Please set it first.{Style.RESET_ALL}")
    exit(1)

# Initialize Deepgram client
deepgram = Deepgram(DEEPGRAM_API_KEY)

# Comment out OpenAI related code
# OPENAI_API_KEY = "..."
# client = openai.OpenAI(api_key=OPENAI_API_KEY)

async def transcribe_audio_chunk(chunk_path):
    """
    Transcribe a single audio chunk using Deepgram's API with diarization.
    
    Args:
        chunk_path (str): Path to the audio chunk file
        
    Returns:
        str: The transcribed text
    """
    print(f"{Fore.YELLOW}[DEBUG] Transcribing chunk: {chunk_path}{Style.RESET_ALL}")
    
    try:
        with open(chunk_path, "rb") as audio_file:
            options = {
                'smart_format': True,
                'model': 'nova-3',
                'diarize': True,  # Enable speaker diarization
                'utterances': False  # Get per-speaker utterances
            }
            response = await deepgram.transcription.prerecorded({'buffer': audio_file, 'mimetype': 'audio/mp3'}, options)
            
            # Extract transcription with speaker labels
            utterances = response['results']['utterances']
            transcription = ""
            for utterance in utterances:
                speaker = utterance.get('speaker', '0')  # Default to '0' if speaker not identified
                text = utterance.get('transcript', '')
                transcription += f"Speaker {speaker}: {text}\n"
            
            print(f"{Fore.GREEN}[DEBUG] Successfully transcribed chunk with {len(utterances)} utterances{Style.RESET_ALL}")
            return transcription
            
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Chunk transcription failed: {str(e)}{Style.RESET_ALL}")
        return ""

async def transcribe_audio(audio_file_path):
    """
    Transcribe an audio file using Deepgram's API with diarization.
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
        
        with open(audio_file_path, 'rb') as audio:
            source = {'buffer': audio, 'mimetype': 'audio/mp3'}
            options = {
                'smart_format': True,
                'model': 'nova-3',
                'diarize': True,  # Enable speaker diarization
                'utterances': True  # Get per-speaker utterances
            }
            
            response = await deepgram.transcription.prerecorded(source, options)
            
            # Extract transcription with speaker labels
            utterances = response['results']['utterances']
            transcription = ""
            for utterance in utterances:
                speaker = utterance.get('speaker', '0')  # Default to '0' if speaker not identified
                text = utterance.get('transcript', '')
                transcription += f"Speaker {speaker}: {text}\n"
                
            print(f"{Fore.GREEN}[DEBUG] Successfully transcribed audio with {len(utterances)} utterances{Style.RESET_ALL}")
            return transcription
            
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
    
    # 2. Transcribe the MP3 using Deepgram
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
    
    # Load the data
    try:
        with open('video-data-missing.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"{Fore.GREEN}[INFO] Loaded data with {len(data)} items{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to load data: {str(e)}{Style.RESET_ALL}")
        return

    # Configure concurrent processing
    BATCH_SIZE = 10  # Process 10 items per batch
    MAX_CONCURRENT_CALLS = 8  # Process 8 concurrent calls
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
    success_count = 0
    start_index = 0
    # end_index = 110

    print(f"{Fore.CYAN}[INFO] Starting from item {start_index + 1} out of {len(data)} items{Style.RESET_ALL}")

    # Modify process_item to use semaphore
    async def process_item_with_semaphore(item, i, total_items):
        async with semaphore:
            return await process_item(item, i, total_items)

    # Process items in batches
    remaining_items = data[start_index:]
    for batch_start in range(0, len(remaining_items), BATCH_SIZE):
        batch = remaining_items[batch_start:batch_start + BATCH_SIZE]
        batch_tasks = []
        
        # Create tasks for each item in the batch
        for idx, item in enumerate(batch):
            global_idx = start_index + batch_start + idx
            task = process_item_with_semaphore(item, global_idx, len(data))
            batch_tasks.append(task)
        
        # Process batch concurrently
        batch_results = await asyncio.gather(*batch_tasks)
        success_count += sum(1 for result in batch_results if result)

        # Save after each batch
        try:
            with open('./video-data-missing-gotten.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"{Fore.GREEN}[INFO] Saved updated data after processing batch{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[INFO] {success_count} items transcribed, {len(data) - (batch_start + start_index + len(batch))} items remaining{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to save data: {str(e)}{Style.RESET_ALL}")

    # Print finalization message
    print(f"\n{Fore.GREEN}[INFO] === FINALIZED ===={Style.RESET_ALL}")
    print(f"{Fore.GREEN}[INFO] Successfully transcribed {success_count} out of {len(data) - start_index} items processed{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[INFO] Results saved to ./video-data-missing-gotten.json{Style.RESET_ALL}")

def process_data():
    """
    Main function to process the YC video data.
    """
    asyncio.run(process_data_async())

if __name__ == "__main__":
    process_data()
