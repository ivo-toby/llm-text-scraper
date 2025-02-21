import argparse
import hashlib
import os
import pickle
import time

import openai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

parser = argparse.ArgumentParser(
    description="Scrape structured documentation for AI Code generation use."
)
parser.add_argument(
    "--base-url",
    required=True,
    help="Base URL of the documentation site (e.g., https://mastra.ai)",
)
parser.add_argument(
    "--filter-path",
    required=False,
    help="Path filter to scrape specific sections (e.g., /docs/reference/)",
)
parser.add_argument(
    "--custom-selector",
    required=False,
    help="Custom CSS selector to extract content (e.g., '.my-class, #main-content')",
)
args = parser.parse_args()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

BASE_URL = args.base_url.rstrip("/")
DOCS_ROOT = f"{BASE_URL}/"
FILTER_PATH = args.filter_path.strip("/") if args.filter_path else ""
OUTPUT_FILE = "llms-full.txt"
TMP_DIR = "./tmp"

os.makedirs(TMP_DIR, exist_ok=True)

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

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
        content = extract_text(
            soup, custom_selector=args.custom_selector
        )  # Pass argument

        if content:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
        return content
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def extract_text(soup, custom_selector=None):
    """Extracts main documentation content with optional user-defined selector."""
    if not soup:
        return ""

    if custom_selector:
        custom_content = soup.select_one(custom_selector)
        if custom_content:
            extracted_text = custom_content.get_text(separator="\n").strip()
            if len(extracted_text) > 50:
                return extracted_text

    # Fallback selectors for extracting content from various doc layouts
    possible_selectors = [
        "article",  # Common in blogs and structured docs
        "div.col-content",  # Contentful-style docs
        "div.markdown-body",  # GitHub/GitBook-style docs
        "section.main-content",  # Some dev docs use sections
        "div.doc-content",  # Other documentation platforms
        "main",  # Generic fallback
    ]

    for selector in possible_selectors:
        content = soup.select_one(selector)
        if content:
            extracted_text = content.get_text(separator="\n").strip()
            if len(extracted_text) > 50:
                return extracted_text

    # Last resort: Get the longest text-heavy div
    divs = soup.find_all("div")
    if divs:
        largest_div = max(divs, key=lambda d: len(d.get_text()), default=None)
        if largest_div:
            extracted_text = largest_div.get_text(separator="\n").strip()
            if len(extracted_text) > 50:
                return extracted_text

    return ""


def extract_links():
    """Finds all documentation links from the page."""
    print("🌐 Fetching dynamic links ...")

    driver.get(BASE_URL)  # Scrape from the provided base URL
    time.sleep(2)

    links = set()
    elements = driver.find_elements(By.TAG_NAME, "a")
    for elem in elements:
        href = elem.get_attribute("href")
        if href and href.startswith(BASE_URL):
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
    - Compress output to be concise and informative, but still reduces the amount of tokens needed when used by a LLM
    - Remove any unnecessary or redundant text.

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
    """Crawls URL to gather all links before processing, using caching."""
    cache_file = os.path.join(TMP_DIR, "urls_cache.pkl")

    if os.path.exists(cache_file):
        print("📂 Using cached URL list...")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    all_urls = extract_links()

    filtered_urls = [url for url in all_urls if not FILTER_PATH or FILTER_PATH in url]

    filtered_urls.sort(key=lambda x: (x.count("/"), x))

    with open(cache_file, "wb") as cacheFile:
        pickle.dump(filtered_urls, cacheFile)

    return filtered_urls


def scrape_and_structure(urls):
    """Scrapes and structures the documentation for better intepretation by AI Code generation tools."""
    structured_text = ""

    for url in urls:
        content = fetch_page(url)
        if not content:
            continue

        processed_text = process_with_llm(content)

        structured_text += f"\n\n{'-' * 40}\n"
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
