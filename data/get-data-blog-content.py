import json
import time
from termcolor import colored
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def scrape_yc_blog_data(input_json='tc-blog-data.json', output_json='yc-blog-data-extracted.json'):
    print(colored(f"Starting scrape_yc_blog_data with input: {input_json}", "blue"))
    
    # 1. Read original JSON data
    with open(input_json, 'r', encoding='utf-8') as f:
        blog_data = json.load(f)
    print(colored(f"Loaded {len(blog_data)} items from {input_json}", "green"))

    # 2. Set up Selenium (example: using Chrome in headless mode)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # run browser headless (no UI)
    # If needed, specify the path to your chromedriver with executable_path:
    # driver = webdriver.Chrome(options=chrome_options, executable_path='/path/to/chromedriver')
    driver = webdriver.Chrome(options=chrome_options)
    print(colored("Initialized Chrome driver in headless mode", "green"))

    for i, item in enumerate(blog_data):
        url = item.get("page_url")
        if not url:
            print(colored(f"Skipping item {i} - no URL found", "yellow"))
            continue

        try:
            print(colored(f"Processing URL ({i+1}/{len(blog_data)}): {url}", "blue"))
            
            # 3. Open the page URL with Selenium
            driver.get(url)

            # Wait a bit for dynamic content to load, if needed
            time.sleep(2)

            # 4. Parse the page source with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # A) Extract Table of Contents (if it exists)
            table_of_contents_list = []
            details_toc = soup.find('details')
            if details_toc:
                li_tags = details_toc.select('li.pl-3')
                for li in li_tags:
                    toc_text = li.get_text(strip=True)
                    if toc_text:
                        table_of_contents_list.append(toc_text)
            print(colored(f"Found {len(table_of_contents_list)} TOC items", "green"))

            # B) Extract the Title
            title_el = soup.find('h1', class_='ycdc-page-title')
            title_text = title_el.get_text(strip=True) if title_el else ""
            print(colored(f"Extracted title: {title_text[:50]}...", "green"))

            # C) Extract the main blog text
            main_content_el = soup.select_one('div.prose')
            whole_content_text = main_content_el.get_text("\n", strip=True) if main_content_el else ""
            print(colored(f"Extracted content length: {len(whole_content_text)} chars", "green"))

            # D) Update item with content and save immediately
            item["content"] = {
                "table_of_contents": table_of_contents_list,
                "whole_content": whole_content_text
            }
            
            # Save after each successful item extraction
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(blog_data, f, indent=2, ensure_ascii=False)
            print(colored(f"Saved progress after processing item {i+1}", "green"))

        except Exception as e:
            print(colored(f"Error scraping {url}: {e}", "red"))
            item["content"] = {
                "table_of_contents": [],
                "whole_content": ""
            }
            # Save even after errors to preserve progress
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(blog_data, f, indent=2, ensure_ascii=False)
            print(colored(f"Saved progress after error on item {i+1}", "yellow"))

    # 5. Close the Selenium driver
    driver.quit()
    print(colored("Closed Chrome driver", "green"))

    print(colored(f"Successfully completed data extraction to {output_json}", "green"))


if __name__ == "__main__":
    print(colored("Starting blog content extraction script", "blue"))
    scrape_yc_blog_data(
        input_json='tc-blog-data.json',
        output_json='yc-blog-data-extracted.json'
    )
    print(colored("Finished blog content extraction script", "blue"))
