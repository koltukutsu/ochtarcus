import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def scrape_yc_blog_data(input_json='tc-blog-data.json', output_json='yc-blog-data-extracted.json'):
    # 1. Read original JSON data
    with open(input_json, 'r', encoding='utf-8') as f:
        blog_data = json.load(f)

    # 2. Set up Selenium (example: using Chrome in headless mode)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # run browser headless (no UI)
    # If needed, specify the path to your chromedriver with executable_path:
    # driver = webdriver.Chrome(options=chrome_options, executable_path='/path/to/chromedriver')
    driver = webdriver.Chrome(options=chrome_options)

    for item in blog_data:
        url = item.get("page_url")
        if not url:
            # Skip if no URL
            continue

        try:
            # 3. Open the page URL with Selenium
            driver.get(url)

            # Wait a bit for dynamic content to load, if needed
            time.sleep(2)

            # 4. Parse the page source with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # A) Extract Table of Contents (if it exists)
            #    From the snippet, the <details> containing the Table of Contents often
            #    has summary text "Table of Contents" or a <h5> tag "Table of Contents".
            table_of_contents_list = []
            details_toc = soup.find('details')
            if details_toc:
                # Look for all <li> inside that details block
                li_tags = details_toc.select('li.pl-3')
                for li in li_tags:
                    # Extract the text
                    toc_text = li.get_text(strip=True)
                    if toc_text:
                        table_of_contents_list.append(toc_text)

            # B) Extract the Title
            #    The snippet shows <h1 class="ycdc-page-title">…</h1>
            title_el = soup.find('h1', class_='ycdc-page-title')
            title_text = title_el.get_text(strip=True) if title_el else ""

            # C) Extract the main blog text
            #    The snippet shows the main content inside <div class="prose …">
            main_content_el = soup.select_one('div.prose')
            whole_content_text = main_content_el.get_text("\n", strip=True) if main_content_el else ""

            # If you also want the final text to include the h1 title, you can prepend it:
            #   whole_content_text = title_text + "\n\n" + whole_content_text

            # D) Prepare the 'content' dict and update item
            item["content"] = {
                "table_of_contents": table_of_contents_list,
                "whole_content": whole_content_text
            }

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            # Optionally store some default or partial result
            item["content"] = {
                "table_of_contents": [],
                "whole_content": ""
            }

    # 5. Close the Selenium driver
    driver.quit()

    # 6. Write out the final JSON with the new content appended
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(blog_data, f, indent=2, ensure_ascii=False)

    print(f"Saved augmented data to {output_json}")


if __name__ == "__main__":
    scrape_yc_blog_data(
        input_json='tc-blog-data.json',
        output_json='yc-blog-data-extracted.json'
    )
