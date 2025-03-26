import json

def find_missing_transcriptions():
    try:
        # Load the JSON file
        with open('video-data-updated-5.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Keep track of items without transcription
        missing_items = []
        
        # Go through each item
        for index, item in enumerate(data):
            if 'mp3_content' not in item or not item['mp3_content']:
                missing_items.append({
                    'index': index,
                    'name': item.get('name_video', 'Unnamed')
                })
        
        # Print results
        print(f"\nItems missing transcription:")
        print("-" * 50)
        for item in missing_items:
            print(f"Index {item['index']}: {item['name']}")
        
        print(f"\nTotal items missing transcription: {len(missing_items)}")
        print(f"Total items in dataset: {len(data)}")
        print(f"Completion percentage: {((len(data) - len(missing_items)) / len(data) * 100):.2f}%")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    find_missing_transcriptions()