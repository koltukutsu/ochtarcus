import os
import json
import requests
from bs4 import BeautifulSoup
from pytube import YouTube
from urllib.parse import urlparse, parse_qs

def download_youtube_as_mp3(youtube_url, output_filename):
    """
    Downloads the YouTube video at youtube_url as an MP3 file
    named output_filename in the 'downloaded' folder. 
    """
    # Ensure 'downloaded' directory exists
    os.makedirs('downloaded', exist_ok=True)
    
    # Use pytube to download only the audio stream
    yt = YouTube(youtube_url)
    audio_stream = yt.streams.filter(only_audio=True).first()
    
    # Download the file
    downloaded_file = audio_stream.download(output_path='downloaded')
    
    # Rename the file extension from (e.g. .mp4) to .mp3
    base, ext = os.path.splitext(downloaded_file)
    new_file = os.path.join('downloaded', output_filename + '.mp3')
    os.rename(downloaded_file, new_file)
    
    return new_file

def extract_youtube_link_from_html(html_content):
    """
    Extract the first YouTube embed link from the given HTML content.
    Returns the standard watch URL if found, else None.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    # Look for an iframe whose 'src' contains 'youtube.com'
    iframe = soup.find('iframe', src=lambda x: x and 'youtube.com' in x)
    if not iframe:
        return None
    
    embed_src = iframe['src']
    # Sometimes the src might be something like:
    #   https://www.youtube.com/embed/VIDEOID?query=params
    # We'll parse out the VIDEOID and convert to a normal watch link
    parsed = urlparse(embed_src)
    
    # The video ID is typically the last part of the path in '/embed/VIDEOID'
    # Alternatively, if you prefer, you can pass the embed link directly to pytube
    # Pytube usually can handle that. But let's extract a normal watch link:
    if '/embed/' in parsed.path:
        video_id = parsed.path.split('/')[-1]  # last part after /embed/
        watch_url = f'https://youtube.com/watch?v={video_id}'
        return watch_url
    
    # Fallback: Just return the raw embed link
    return embed_src

def main():
    # 1) Load the JSON data
    with open('yc-video-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_data = []

    for item in data:
        # 2) Build the final URL by prepending https://www.ycombinator.com/
        original_path = item.get('url', '')
        final_url = 'https://www.ycombinator.com/' + original_path
        
        # Fetch the HTML
        response = requests.get(final_url)
        if response.status_code != 200:
            print(f"Failed to fetch {final_url}")
            continue
        
        html_content = response.text
        
        # 3) Extract the YouTube link from the HTML
        youtube_link = extract_youtube_link_from_html(html_content)
        if not youtube_link:
            print(f"No YouTube link found on {final_url}")
            continue
        
        # 4) Download the video as an MP3
        #    We'll use something from the item as the file’s name:
        #    e.g., item['name'] or item['title']. Adjust as needed.
        #    Here we’ll assume there's a 'title' or similar. If not, change it!
        mp3_filename = item.get('title', 'untitled_video').replace(' ', '_')
        
        try:
            saved_mp3_path = download_youtube_as_mp3(youtube_link, mp3_filename)
        except Exception as e:
            print(f"Error downloading {youtube_link}: {e}")
            continue
        
        # 5) Store the YouTube link in the item dictionary
        #    Also optionally store the local MP3 path.
        item['youtube_url'] = youtube_link
        item['mp3_file'] = saved_mp3_path
        
        updated_data.append(item)
    
    # 6) Save the updated list of dictionaries
    with open('yc-video-data-downloaded.json', 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()
