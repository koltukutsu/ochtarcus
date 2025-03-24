import json
import os
import time
import asyncio
import argparse
from colorama import init, Fore, Style
import openai
from dotenv import load_dotenv

# Initialize colorama for colored output
init()

# Load environment variables (for OpenAI API key)
load_dotenv()

# Get OpenAI API key from environment variable
OPENAI_API_KEY = "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"
if not OPENAI_API_KEY:
    print(f"{Fore.RED}[ERROR] OPENAI_API_KEY not found. Please set it first.{Style.RESET_ALL}")
    exit(1)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Supported languages - you can add more here
SUPPORTED_LANGUAGES = {
    "turkish": "Turkish",
    "french": "French",
    "spanish": "Spanish",
    "german": "German",
    "italian": "Italian",
    "portuguese": "Portuguese",
    "russian": "Russian",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "korean": "Korean",
    # Add more languages as needed
}

# Default language for translation
DEFAULT_LANGUAGE = "turkish"

async def translate_text(text, target_language, chunk_size=4000, retry_count=3):
    """
    Translate text using OpenAI's API.
    
    Args:
        text (str): Text to translate
        target_language (str): Target language
        chunk_size (int): Maximum characters per chunk
        retry_count (int): Number of retries if API call fails
        
    Returns:
        str: The translated text
    """
    if not text or len(text.strip()) == 0:
        return ""
    
    # For very large texts, split them into chunks
    if len(text) > chunk_size:
        print(f"{Fore.YELLOW}[DEBUG] Text is too large ({len(text)} chars). Splitting into chunks.{Style.RESET_ALL}")
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        
        # Translate each chunk
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"{Fore.YELLOW}[DEBUG] Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars){Style.RESET_ALL}")
            translated_chunk = await translate_text(chunk, target_language)
            translated_chunks.append(translated_chunk)
        
        return "".join(translated_chunks)
    
    # Perform the translation with retries
    for attempt in range(retry_count):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a professional translator. Translate the text into {target_language} while preserving formatting, such as line breaks, paragraph structure, and any markdown formatting."},
                    {"role": "user", "content": f"Translate the following text to {target_language}:\n\n{text}"}
                ],
                temperature=0.3,
                max_tokens=4096
            )
            
            translated_text = response.choices[0].message.content
            return translated_text
        
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Translation failed (attempt {attempt+1}/{retry_count}): {str(e)}{Style.RESET_ALL}")
            if attempt < retry_count - 1:
                wait_time = 2 * (attempt + 1)  # Exponential backoff
                print(f"{Fore.YELLOW}[DEBUG] Retrying in {wait_time} seconds...{Style.RESET_ALL}")
                time.sleep(wait_time)
            else:
                return f"[TRANSLATION ERROR] {text[:100]}..."
    
    # If all retries fail, return this message
    return f"[TRANSLATION FAILED] {text[:100]}..."

async def translate_video_data(video_data, target_language):
    """
    Translate relevant fields in video data.
    
    Args:
        video_data (dict): Video data item
        target_language (str): Target language
        
    Returns:
        dict: Translated video data
    """
    print(f"{Fore.CYAN}[INFO] Translating video: {video_data.get('name_video', 'Unnamed')}{Style.RESET_ALL}")
    
    # Create a deep copy to avoid modifying original data
    translated_item = video_data.copy()
    
    # List of fields to translate
    fields_to_translate = [
        ('name_video', 'name_video'),
        ('description_video', 'description_video')
    ]
    
    # Check if mp3_content exists and add it to fields to translate
    if 'mp3_content' in video_data and video_data['mp3_content']:
        fields_to_translate.append(('mp3_content', 'mp3_content'))
    
    # Translate each field
    for original_field, target_field in fields_to_translate:
        if original_field in video_data and video_data[original_field]:
            print(f"{Fore.YELLOW}[DEBUG] Translating field: {original_field} ({len(str(video_data[original_field]))} chars){Style.RESET_ALL}")
            translated_item[target_field] = await translate_text(str(video_data[original_field]), target_language)
    
    return translated_item

async def translate_blog_data(blog_data, target_language):
    """
    Translate relevant fields in blog data.
    
    Args:
        blog_data (dict): Blog data item
        target_language (str): Target language
        
    Returns:
        dict: Translated blog data
    """
    print(f"{Fore.CYAN}[INFO] Translating blog: {blog_data.get('name_blog', 'Unnamed')}{Style.RESET_ALL}")
    
    # Create a deep copy to avoid modifying original data
    translated_item = blog_data.copy()
    
    # Fields to translate
    fields_to_translate = [
        ('name_blog', 'name_blog'),
        ('description_blog', 'description_blog')
    ]
    
    # Translate each field
    for original_field, target_field in fields_to_translate:
        if original_field in blog_data and blog_data[original_field]:
            print(f"{Fore.YELLOW}[DEBUG] Translating field: {original_field} ({len(str(blog_data[original_field]))} chars){Style.RESET_ALL}")
            translated_item[target_field] = await translate_text(str(blog_data[original_field]), target_language)
    
    # Translate blog content if it exists
    if 'content' in blog_data and 'whole_content' in blog_data['content'] and blog_data['content']['whole_content']:
        print(f"{Fore.YELLOW}[DEBUG] Translating blog content ({len(blog_data['content']['whole_content'])} chars){Style.RESET_ALL}")
        
        # Create a copy of the content structure
        translated_item['content'] = blog_data['content'].copy()
        
        # Translate table of contents if it exists
        if 'table_of_contents' in blog_data['content']:
            translated_toc = []
            for toc_item in blog_data['content']['table_of_contents']:
                translated_toc_item = await translate_text(toc_item, target_language)
                translated_toc.append(translated_toc_item)
            translated_item['content']['table_of_contents'] = translated_toc
        
        # Translate the whole content
        translated_item['content']['whole_content'] = await translate_text(
            blog_data['content']['whole_content'], 
            target_language
        )
    
    return translated_item

async def process_data_async(target_language):
    """
    Process and translate both video and blog data.
    
    Args:
        target_language (str): Target language for translation
    """
    print(f"{Fore.CYAN}[INFO] Starting translation process to {target_language}{Style.RESET_ALL}")
    
    # Create translation directory structure
    translation_dir = os.path.join("translation", target_language.lower())
    os.makedirs(translation_dir, exist_ok=True)
    
    # Process video data
    try:
        # Load video data
        with open('video-data-updated.json', 'r', encoding='utf-8') as f:
            video_data = json.load(f)
        print(f"{Fore.GREEN}[INFO] Loaded video data with {len(video_data)} items{Style.RESET_ALL}")
        
        # Translate video data
        translated_video_data = []
        for i, item in enumerate(video_data):
            print(f"{Fore.CYAN}[INFO] Processing video item {i+1}/{len(video_data)}{Style.RESET_ALL}")
            translated_item = await translate_video_data(item, target_language)
            translated_video_data.append(translated_item)
            
            # Save progress periodically (every 5 items)
            if (i+1) % 5 == 0 or i == len(video_data) - 1:
                video_output_path = os.path.join(translation_dir, "video-data.json")
                with open(video_output_path, 'w', encoding='utf-8') as f:
                    json.dump(translated_video_data, f, indent=2, ensure_ascii=False)
                print(f"{Fore.GREEN}[INFO] Saved progress: {i+1}/{len(video_data)} video items translated{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}[INFO] Completed translation of video data to {target_language}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to process video data: {str(e)}{Style.RESET_ALL}")
    
    # Process blog data
    try:
        # Load blog data
        with open('blog-data.json', 'r', encoding='utf-8') as f:
            blog_data = json.load(f)
        print(f"{Fore.GREEN}[INFO] Loaded blog data with {len(blog_data)} items{Style.RESET_ALL}")
        
        # Translate blog data
        translated_blog_data = []
        for i, item in enumerate(blog_data):
            print(f"{Fore.CYAN}[INFO] Processing blog item {i+1}/{len(blog_data)}{Style.RESET_ALL}")
            translated_item = await translate_blog_data(item, target_language)
            translated_blog_data.append(translated_item)
            
            # Save progress periodically (every 5 items)
            if (i+1) % 5 == 0 or i == len(blog_data) - 1:
                blog_output_path = os.path.join(translation_dir, "blog-data.json")
                with open(blog_output_path, 'w', encoding='utf-8') as f:
                    json.dump(translated_blog_data, f, indent=2, ensure_ascii=False)
                print(f"{Fore.GREEN}[INFO] Saved progress: {i+1}/{len(blog_data)} blog items translated{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}[INFO] Completed translation of blog data to {target_language}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to process blog data: {str(e)}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}[INFO] === TRANSLATION COMPLETED ===={Style.RESET_ALL}")
    print(f"{Fore.GREEN}[INFO] All data has been translated to {target_language}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[INFO] Results saved to translation/{target_language.lower()}/{Style.RESET_ALL}")

def main():
    """
    Main function to handle command line arguments and start the translation process.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Translate video and blog data to different languages')
    parser.add_argument('--language', type=str, default=DEFAULT_LANGUAGE,
                        help=f'Target language for translation (default: {DEFAULT_LANGUAGE})')
    parser.add_argument('--list-languages', action='store_true',
                        help='List all supported languages')
    args = parser.parse_args()
    
    # List all supported languages if requested
    if args.list_languages:
        print(f"{Fore.CYAN}[INFO] Supported languages:{Style.RESET_ALL}")
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            print(f"  - {lang_code} ({lang_name})")
        return
    
    # Check if the specified language is supported
    target_language = args.language.lower()
    if target_language not in SUPPORTED_LANGUAGES:
        print(f"{Fore.RED}[ERROR] Unsupported language: {target_language}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[INFO] Use --list-languages to see all supported languages{Style.RESET_ALL}")
        return
    
    # Start the translation process
    asyncio.run(process_data_async(SUPPORTED_LANGUAGES[target_language]))

if __name__ == "__main__":
    main()