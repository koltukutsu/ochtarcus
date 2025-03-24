import os
import json
import requests
from bs4 import BeautifulSoup
from pytube import YouTube
from urllib.parse import urlparse, parse_qs
from colorama import init, Fore, Style
import yt_dlp
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Initialize colorama
init()

def download_youtube_as_mp3(youtube_url, output_filename):
    """
    Downloads the YouTube video at youtube_url as an MP3 file
    named output_filename in the 'downloaded' folder. 
    """
    print(f"{Fore.CYAN}[DEBUG] Starting download for YouTube URL: {youtube_url}{Style.RESET_ALL}")
    
    # Ensure 'downloaded' directory exists
    os.makedirs('downloaded', exist_ok=True)
    print(f"{Fore.GREEN}[DEBUG] Created/verified 'downloaded' directory{Style.RESET_ALL}")
    
    # Configure yt-dlp options
    output_path = os.path.join('downloaded', output_filename + '.mp3')
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path[:-4],  # Remove .mp3 as yt-dlp will add it
        'quiet': False,
        'no_warnings': False
    }
    
    # Download the audio
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        print(f"{Fore.GREEN}[DEBUG] Downloaded file to: {output_path}{Style.RESET_ALL}")
        return output_path
    except Exception as e:
        print(f"{Fore.RED}[DEBUG] Error with yt-dlp: {e}{Style.RESET_ALL}")
        raise

def extract_youtube_link_with_selenium(url):
    """
    Uses Selenium to load the page, click on the YouTube thumbnail,
    and extract the video URL after it loads.
    """
    print(f"{Fore.CYAN}[DEBUG] Starting Selenium to interact with: {url}{Style.RESET_ALL}")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        print(f"{Fore.GREEN}[DEBUG] Loaded page with Selenium{Style.RESET_ALL}")
        
        # Wait a moment for page to fully load
        time.sleep(2)
        
        # Look for YouTube thumbnail/play button and click it
        # Try several possible selectors
        selectors = [
            "//div[contains(@class, 'ytp-cued-thumbnail-overlay-image')]",  # YouTube thumbnail overlay
            "//button[contains(@class, 'ytp-large-play-button')]",  # YouTube play button
            "//div[contains(@class, 'ytplayer')]",  # YouTube player div
            "//div[contains(@id, 'ytplayer')]",  # YouTube player by ID
            "//iframe[contains(@src, 'youtube.com')]",  # YouTube iframe
            "//div[contains(@class, 'video-stream')]",  # Video stream element
            "//div[contains(@class, 'html5-video-player')]"  # HTML5 video player
        ]
        
        clicked = False
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"{Fore.YELLOW}[DEBUG] Found clickable element with selector: {selector}{Style.RESET_ALL}")
                    elements[0].click()
                    print(f"{Fore.GREEN}[DEBUG] Clicked on element{Style.RESET_ALL}")
                    clicked = True
                    # Wait for video to load
                    time.sleep(3)
                    break
            except Exception as e:
                print(f"{Fore.YELLOW}[DEBUG] Could not click selector {selector}: {e}{Style.RESET_ALL}")
        
        if not clicked:
            print(f"{Fore.RED}[DEBUG] Could not find any clickable YouTube elements{Style.RESET_ALL}")
        
        # After clicking, use various methods to find the YouTube URL
        
        # Method 1: Look for video element with src attribute
        video_elements = driver.find_elements(By.TAG_NAME, "video")
        for video in video_elements:
            src = video.get_attribute("src")
            if src and "youtube.com" in src:
                print(f"{Fore.GREEN}[DEBUG] Found video src: {src}{Style.RESET_ALL}")
                driver.quit()
                return src
        
        # Method 2: Check iframe src after click
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and "youtube.com/embed/" in src:
                print(f"{Fore.GREEN}[DEBUG] Found iframe src after click: {src}{Style.RESET_ALL}")
                video_id = src.split("/embed/")[1].split("?")[0]
                watch_url = f"https://youtube.com/watch?v={video_id}"
                driver.quit()
                return watch_url
        
        # Method 3: Get page source after clicking and extract with BeautifulSoup
        html_content = driver.page_source
        youtube_link = extract_youtube_link_from_html(html_content)
        if youtube_link:
            print(f"{Fore.GREEN}[DEBUG] Found YouTube link from HTML after clicking: {youtube_link}{Style.RESET_ALL}")
            driver.quit()
            return youtube_link
        
        # Method 4: Look for data attributes that might contain the video ID
        elements_with_data = driver.find_elements(By.XPATH, "//*[@data-video-id]")
        if elements_with_data:
            video_id = elements_with_data[0].get_attribute("data-video-id")
            watch_url = f"https://youtube.com/watch?v={video_id}"
            print(f"{Fore.GREEN}[DEBUG] Found video ID from data attribute: {watch_url}{Style.RESET_ALL}")
            driver.quit()
            return watch_url
        
        driver.quit()
        print(f"{Fore.RED}[DEBUG] Could not extract YouTube URL after clicking{Style.RESET_ALL}")
        return None
    
    except Exception as e:
        print(f"{Fore.RED}[DEBUG] Selenium error: {e}{Style.RESET_ALL}")
        if 'driver' in locals():
            driver.quit()
        return None

def extract_youtube_link_from_html(html_content):
    """
    Extract the first YouTube embed link from the given HTML content.
    Returns the standard watch URL if found, else None.
    """
    print(f"{Fore.CYAN}[DEBUG] Starting YouTube link extraction from HTML{Style.RESET_ALL}")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: Look for an iframe whose 'src' contains 'youtube.com'
    iframe = soup.find('iframe', src=lambda x: x and 'youtube.com' in x)
    if iframe:
        embed_src = iframe['src']
        print(f"{Fore.YELLOW}[DEBUG] Found embed source from iframe: {embed_src}{Style.RESET_ALL}")
        
        # Sometimes the src might be something like:
        #   https://www.youtube.com/embed/VIDEOID?query=params
        # We'll parse out the VIDEOID and convert to a normal watch link
        parsed = urlparse(embed_src)
        
        if '/embed/' in parsed.path:
            video_id = parsed.path.split('/')[-1]  # last part after /embed/
            watch_url = f'https://youtube.com/watch?v={video_id}'
            print(f"{Fore.GREEN}[DEBUG] Converted iframe to watch URL: {watch_url}{Style.RESET_ALL}")
            return watch_url
    
    # Method 2: Look for thumbnail overlay image
    thumbnail_divs = soup.find_all('div', class_='ytp-cued-thumbnail-overlay-image')
    for thumbnail in thumbnail_divs:
        style = thumbnail.get('style', '')
        # Look for URL in the style attribute
        url_match = re.search(r'url\(["\']?(https://i\.ytimg\.com/vi/([^/]+)/[^"\']+)["\']?\)', style)
        if url_match:
            thumbnail_url = url_match.group(1)
            video_id = url_match.group(2)
            print(f"{Fore.YELLOW}[DEBUG] Found thumbnail image: {thumbnail_url}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[DEBUG] Extracted video ID: {video_id}{Style.RESET_ALL}")
            watch_url = f'https://youtube.com/watch?v={video_id}'
            print(f"{Fore.GREEN}[DEBUG] Created watch URL from thumbnail: {watch_url}{Style.RESET_ALL}")
            return watch_url
    
    # Method 3: Look for video elements and check for parent containers with data-video-id
    video_elements = soup.find_all('video')
    for video in video_elements:
        # Look for parent containers with video ID
        parent = video.parent
        while parent and parent.name:
            video_id = parent.get('data-video-id')
            if video_id:
                print(f"{Fore.YELLOW}[DEBUG] Found video element with ID: {video_id}{Style.RESET_ALL}")
                watch_url = f'https://youtube.com/watch?v={video_id}'
                print(f"{Fore.GREEN}[DEBUG] Created watch URL from video element: {watch_url}{Style.RESET_ALL}")
                return watch_url
            parent = parent.parent
    
    # Method 4: Look for any elements with data attributes related to YouTube
    youtube_elements = soup.find_all(attrs={"data-video-id": True})
    if youtube_elements:
        video_id = youtube_elements[0]['data-video-id']
        print(f"{Fore.YELLOW}[DEBUG] Found element with data-video-id: {video_id}{Style.RESET_ALL}")
        watch_url = f'https://youtube.com/watch?v={video_id}'
        print(f"{Fore.GREEN}[DEBUG] Created watch URL from data attribute: {watch_url}{Style.RESET_ALL}")
        return watch_url
    
    # If we got here, no YouTube video was found
    print(f"{Fore.RED}[DEBUG] No YouTube video found in HTML{Style.RESET_ALL}")
    return None

def main():
    print(f"{Fore.CYAN}[DEBUG] Starting main execution{Style.RESET_ALL}")
    
    # 1) Load the JSON data
    with open('yc-video-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"{Fore.GREEN}[DEBUG] Loaded JSON data with {len(data)} items{Style.RESET_ALL}")
    
    updated_data = []

    for i, item in enumerate(data, 1):
        print(f"\n{Fore.CYAN}[DEBUG] Processing item {i} of {len(data)}{Style.RESET_ALL}")
        
        # 2) Build the final URL by prepending https://www.ycombinator.com/
        original_path = item.get('page_url', '')
        final_url = 'https://www.ycombinator.com' + original_path
        print(f"{Fore.YELLOW}[DEBUG] Processing URL: {final_url}{Style.RESET_ALL}")
        
        # 3) First try using Selenium to interact with the page and get the YouTube link
        youtube_link = extract_youtube_link_with_selenium(final_url)
        
        print(f"\n{Fore.CYAN}[DEBUG] YouTube link extraction status for item {i}:{Style.RESET_ALL}")
        # 4) If Selenium approach fails, try the static HTML approach as fallback
        if not youtube_link:
            print(f"{Fore.YELLOW}[DEBUG] Selenium approach failed, trying static HTML approach{Style.RESET_ALL}")
            # Fetch the HTML
            response = requests.get(final_url)
            if response.status_code != 200:
                print(f"{Fore.RED}[DEBUG] Failed to fetch {final_url}{Style.RESET_ALL}")
                continue
            
            html_content = response.text
            print(f"{Fore.GREEN}[DEBUG] Successfully fetched HTML content{Style.RESET_ALL}")
            
            # Extract the YouTube link from the HTML
            youtube_link = extract_youtube_link_from_html(html_content)
            
        if not youtube_link:
            print(f"{Fore.RED}[DEBUG] No YouTube link found on {final_url}{Style.RESET_ALL}")
            continue
        
        print(f"\n{Fore.CYAN}[DEBUG] Starting download for item {i}:{Style.RESET_ALL}")
        # 5) Download the video as an MP3
        mp3_filename = item.get('name_video', 'untitled_video').replace(' ', '_')
        print(f"{Fore.YELLOW}[DEBUG] Using filename: {mp3_filename}{Style.RESET_ALL}")
        
        try:
            saved_mp3_path = download_youtube_as_mp3(youtube_link, mp3_filename)
            print(f"{Fore.GREEN}[DEBUG] Successfully downloaded MP3 to: {saved_mp3_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[DEBUG] Error downloading {youtube_link}: {e}{Style.RESET_ALL}")
            continue
        
        # 6) Store the YouTube link in the item dictionary
        item['youtube_url'] = youtube_link
        item['mp3_file'] = saved_mp3_path
        
        updated_data.append(item)
        print(f"{Fore.GREEN}[DEBUG] Added item {i} to updated data{Style.RESET_ALL}")
        
        # Save both JSON files after each successful download
        with open('yc-video-data-downloaded.json', 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        with open('yc-video-data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"{Fore.GREEN}[DEBUG] Updated both JSON files after item {i}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}[DEBUG] Completed processing all {len(data)} items{Style.RESET_ALL}")

if __name__ == '__main__':
    main()
