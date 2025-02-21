import argparse
import hashlib
import os
import pickle
import time
from urllib.parse import urljoin

import openai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Argument parsing
parser = argparse.ArgumentParser(
    description="Scrape structured documentation for AI training."
)
parser.add_argument(
    "--base-url",
    required=True,
    help="Base URL of the documentation site (e.g., https://mastra.ai)",
)
parser.add_argument(
    "--filter-path",
    required=True,
    help="Path filter to scrape specific sections (e.g., /docs/reference/)",
)
args = parser.parse_args()

# OpenAI API Key (Ensure this is set in your environment variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

BASE_URL = args.base_url.rstrip("/")  # Remove trailing slash if exists
DOCS_ROOT = f"{BASE_URL}/docs"
FILTER_PATH = args.filter_path.strip("/")  # Remove leading/trailing slashes if exists
OUTPUT_FILE = "llms-full.txt"
TMP_DIR = "./tmp"

# Ensure tmp directory exists
os.makedirs(TMP_DIR, exist_ok=True)

# Configure Selenium (Headless Chrome)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def generate_cache_filename(url):
    """Generate a unique filename for caching based on the URL hash."""
    return os.path.join(TMP_DIR, hashlib.md5(url.encode()).hexdigest() + ".txt")


def fetch_page(url):
    """Fetches a page using Selenium, with caching and retry logic."""
    cache_file = generate_cache_filename(url)

    if os.path.exists(cache_file):
        print(f"📂 Using cached content for {url}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read()

    try:
        print(f"🌐 Fetching {url}...")
        driver.get(url)
        time.sleep(3)  # Allow JavaScript to fully load
        soup = BeautifulSoup(driver.page_source, "html.parser")
        content = extract_text(soup)

        if content:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
        return content
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def extract_text(soup):
    """Extracts main documentation content."""
    if soup:
        content = soup.find("article")  # Adjust selector if necessary
        if content:
            return content.get_text(separator="\n").strip()
    return ""


def extract_links():
    """Finds all dynamically loaded documentation links from the /docs page."""
    print("🌐 Fetching dynamic links from /docs...")
    driver.get(DOCS_ROOT)
    time.sleep(3)

    links = set()
    elements = driver.find_elements(By.TAG_NAME, "a")
    for elem in elements:
        href = elem.get_attribute("href")
        if href and href.startswith(BASE_URL + "/docs/"):
            links.add(href)

    return links


def process_with_llm(text):
    """Uses OpenAI GPT-4o-mini to refine and structure the scraped documentation."""
    prompt = f"""
    You are optimizing technical documentation for AI training.

    TASK:
    - Summarize key points while preserving important technical details.
    - Extract and format API methods, parameters, and example code properly.
    - Ensure clarity, remove redundant or unnecessary text.
    - Format output to be easily understood by Large Language Models (LLMs).

    Raw documentation:
    {text}

    Optimized output:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Error processing with LLM: {e}")
        return text


def get_all_urls():
    """Crawls from /docs to gather all links before processing, using caching."""
    cache_file = os.path.join(TMP_DIR, "urls_cache.pkl")

    if os.path.exists(cache_file):
        print("📂 Using cached URL list...")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    all_urls = extract_links()
    filtered_urls = [url for url in all_urls if FILTER_PATH in url]

    filtered_urls.sort(key=lambda x: (x.count("/"), x))

    with open(cache_file, "wb") as f:
        pickle.dump(filtered_urls, f)

    return filtered_urls


def scrape_and_structure(urls):
    """Scrapes and structures the documentation for better readability."""
    structured_text = ""

    for url in urls:
        content = fetch_page(url)
        if not content:
            continue

        processed_text = process_with_llm(content)
        section_title = (
            url.replace(BASE_URL + f"/docs/{FILTER_PATH}/", "")
            .replace("-", " ")
            .title()
        )

        structured_text += f"\n\n{'-' * 40}\n"
        structured_text += f"{section_title}\n"
        structured_text += f"{url}\n"
        structured_text += f"{'-' * 40}\n\n"
        structured_text += processed_text

    return structured_text


def main():
    """Main function to scrape and save the documentation."""
    print(f"🚀 Gathering all URLs from {BASE_URL} documentation...")
    urls = get_all_urls()

    if not urls:
        print(f"⚠️ No URLs found under {FILTER_PATH}. Exiting.")
        return

    print("🚀 Starting structured documentation scraping...")
    docs_content = scrape_and_structure(urls)

    if docs_content.strip():
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Documentation from {BASE_URL}\n")
            f.write(f"> Extracted content from {FILTER_PATH}\n\n")
            f.write(docs_content.strip())

        print(f"\n✅ Documentation saved to {OUTPUT_FILE}")
    else:
        print(
            "\n⚠️ No content extracted. The website might have additional protections."
        )

    driver.quit()


if __name__ == "__main__":
    main()
