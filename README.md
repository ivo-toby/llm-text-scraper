# 🚀 Universal Documentation Scraper

This script scrapes structured documentation from any website, processes it for AI training, and outputs a well-organized `llms-full.txt` file. It uses **Selenium** to dynamically extract links and **OpenAI GPT-4o-mini** to clean and format the content.

## 🛠 Features

✅ **Scrapes Any Documentation Site** – Just provide a base URL and filter path.  
✅ **Uses JavaScript Rendering** – Extracts dynamically loaded content with Selenium.  
✅ **AI-Powered Processing** – Uses GPT-4o-mini to summarize and format content.  
✅ **Efficient Caching** – Saves URLs and page content to `tmp/` for reuse.  
✅ **Outputs Well-Structured Documentation** – Clear section titles, clean formatting, and code snippets.  
✅ **Supports Custom Content Selectors** – Specify a CSS selector to precisely extract documentation content.

---

## 🔧 Installation

### **1️⃣ Install Prerequisites**

Ensure you have Python 3.8+ installed.

#### Install dependencies:

```bash
pip install selenium webdriver-manager beautifulsoup4 openai chromedriver-autoinstaller
```

#### Set up OpenAI API Key (required for AI processing):

```bash
export OPENAI_API_KEY="your-api-key"
```

Replace `your-api-key` with your actual OpenAI API key.

---

## 🚀 Usage

The script requires two main parameters and an optional one:

- `--base-url` → The website's root documentation URL.
- `--filter-path` → (Optional) The section of the documentation to scrape.
- `--custom-selector` → (Optional) A CSS-style selector for extracting specific content.

### **Basic Usage**

```bash
python scraper.py --base-url https://mastra.ai --filter-path /docs/reference/
```

This will scrape Mastra.ai documentation, filter pages under `/docs/reference/`, and save them in `llms-full.txt`.

### **Scrape Other Sites**

#### OpenAI API Reference:

```bash
python scraper.py --base-url https://platform.openai.com --filter-path /docs/api-reference/
```

#### Vercel AI SDK:

```bash
python scraper.py --base-url https://sdk.vercel.ai --filter-path /docs/
```

### **Using a Custom CSS Selector**

If the default extraction method does not work, you can specify a custom CSS selector.

#### Example: Extracting Content from a Specific `<div>`

```bash
python scraper.py --base-url https://example.com/docs --custom-selector "div.main-doc-container"
```

#### Example: Multiple CSS Selectors

```bash
python scraper.py --base-url https://example.com/docs --custom-selector "article, section.content, div.doc-content"
```

This allows the scraper to precisely target the documentation content.

---

## 🗂 Caching & Refreshing

The script stores scraped URLs and content in the `tmp/` folder to avoid redundant fetching.

- **To force a full refresh**, delete the `tmp/` folder before running the script:

```bash
rm -rf tmp/
```

---

## 📝 Output Format

The extracted content is saved in `llms-full.txt` with a clean structure:

```plaintext
# Documentation from https://mastra.ai
> Extracted content from /docs/reference/

----------------------------------------
Client SDK - JS Overview
https://mastra.ai/docs/reference/client-js
----------------------------------------

(Mastra Client SDK formatted details)

----------------------------------------
RAG Embeddings
https://mastra.ai/docs/reference/rag/embeddings
----------------------------------------

(Formatted RAG documentation)
```

---

## 🛠 Troubleshooting

- **No URLs found?** The site may block automated requests. Try increasing `time.sleep(3)` to `time.sleep(5)` in `fetch_page()`.
- **Content not loading?** Ensure JavaScript-rendered pages are properly fetched by Selenium.
- **Selenium WebDriver Errors?** Run:
  ```bash
  pip install --upgrade webdriver-manager
  ```

---

## 📜 License

This project is open-source and can be used freely.
