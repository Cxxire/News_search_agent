"""
NewsA generater: 
Domain:"aastocks.com""investing.com"
Website:"https://www.aastocks.com/en/","https://hk.investing.com"

"""
from google.adk.agents import Agent
 
from google.adk.tools import google_search
 
from google.adk.agents import Agent
 
import copy
 
from datetime import datetime
 
from typing import Optional
 
from urllib.parse import urlparse
 
from google.adk.agents import LlmAgent
 
from google.adk.agents.callback_context import CallbackContext
 
from google.adk.models import LlmRequest, LlmResponse
 
from google.genai import types
 
from google.adk.tools import google_search
 
from google.genai.types import Content
 
import re
 
# List of allowed domains
 
ALLOWED_DOMAINS = [
 
 
    "aastocks.com",
    "investing.com"
 
]
 
# List of allowed URLs (for stricter matching if needed)
 
ALLOWED_URL_PREFIXES = [
 
    "https://www.aastocks.com/en/",
    "https://hk.investing.com"
 
]
 
def extract_urls(text):
 
    if not isinstance(text, str):
 
        text = str(text)
 
    url_pattern = r'https?://[^\s\)]+'
 
    try:
 
        urls = re.findall(url_pattern, text)
 
    except Exception as e:
 
        print(f"[ERROR] Exception in re.findall: {e}")
 
        urls = []
 
    return urls
 
def is_allowed_domain(url):
 
    try:
 
        domain = urlparse(url).netloc.lower()
 
        # Remove 'www.' if present for comparison
 
        if domain.startswith("www."):
 
            domain = domain[4:]
 
        # Allow subdomains
 
        return any(domain == allowed or domain.endswith('.' + allowed) for allowed in ALLOWED_DOMAINS)
 
    except Exception as e:
 
        print(f"[ERROR] Exception parsing url '{url}': {e}")
 
        return False
 
def filter_news_items(text):
 
    # Try to split by "*Citation:" which is present in your output
 
    news_items = re.split(r'\*Citation:', text)
 
    filtered_items = []
 
    allowed_urls = []
 
    for item in news_items:
 
        # Re-add the citation marker if it was split off
 
        if "http" in item:
 
            citation_split = item.split("http", 1)
 
            if len(citation_split) == 2:
 
                url = "http" + citation_split[1].split()[0]
 
                urls = extract_urls(url)
 
            else:
 
                urls = extract_urls(item)
 
        else:
 
            urls = extract_urls(item)
 
        if not urls:
 
            print(f"[AFTER MODEL] No URL found in news item, skipping: {item[:60]}...")
 
            continue
 
        # Remove the news item if ANY url is not from allowed domains
 
        if all(is_allowed_domain(url) for url in urls):
 
            filtered_items.append(item.strip())
 
            allowed_urls.extend(urls)
 
            print(f"[AFTER MODEL] ✓ News item allowed: {urls}")
 
        else:
 
            print(f"[AFTER MODEL] ✗ News item removed (contains disallowed URL): {item[:60]}...")
 
    return filtered_items, allowed_urls
 
def after_model_callback(callback_context, llm_response):
 
    text = getattr(llm_response, "text", None)
 
    if not text:
 
        text = getattr(llm_response, "content", "")
 
    if not isinstance(text, str):
 
        print(f"[AFTER MODEL] text is type {type(text)}, converting to string.")
 
        text = str(text)
 
    print("[AFTER MODEL] Text being screened for news items:\n", text)
 
    filtered_items, allowed_urls = filter_news_items(text)
 
    if filtered_items:
 
        new_output = '\n\n*Citation:'.join(filtered_items)
 
        print(f"[AFTER MODEL] Filtered news output:\n{new_output}")
 
        setattr(callback_context, "citations", allowed_urls)
 
        if hasattr(llm_response, "text"):
 
            llm_response.text = new_output
 
    else:
 
        print("[AFTER MODEL] No allowed news items found.")
 
        no_news_msg = "No valid news articles found from allowed domains."
 
        if hasattr(llm_response, "text"):
 
            llm_response.text = no_news_msg
 
    return llm_response
 
 
news_analyst = Agent(
 
    name="newsA_agent",
 
    model="gemini-2.5-pro",
 
    description="detail information search agent",
 
    instruction="""
 

    1. Persona
    You are a "Verifiable News Researcher," a specialized research agent. Your purpose is to find and extract news articles based on a specific set of keywords. Your absolute highest priority is verifiability through direct, accessible URLs.

    2. Core Objective
    You will be provided with a set of keywords in [definition_info]. Your task is to find a minimum of 2 and a maximum of 4 news articles that are relevant to these keywords, subject to the constraints below.

    3. Critical Constraints & Rules
    You MUST adhere to every rule without exception.

    Source Constraint: You are ONLY permitted to search the ONLY two websites:

    https://www.aastocks.com/en/
    https://hk.investing.com
    Article Type Constraint (News Only): You MUST select only factual news reports. Discard any articles that are primarily opinion, commentary, editorials, analysis, or interviews. The focus must be on reporting recent events, not interpreting them.

    Dual Recency Constraint (CRITICAL): Articles must be recent in two ways:

    Publication Date: The article itself MUST have been published within the last 7 days from today's date.
    Event Date: The primary events, data, or developments discussed in the article MUST have also occurred within the last 7 days. Discard articles that, despite a recent publication date, are primarily focused on historical events (e.g., an article published yesterday about a financial crisis from last year).
    Relevance Constraint (Keyword-Based): The content of the article must be relevant to the keywords in [definition_info]. An article is considered relevant if it contains one or more of the provided keywords in a meaningful context related to recent events.

    Verifiability & Accessibility Constraint (CRITICAL): Every article you report MUST have a full, direct URL. Before you include an article in your final output, you must verify that its URL is live and accessible. A URL that leads to a "404 Not Found" error, a redirect loop, a "Page moved," or any other error page is considered a complete failure and MUST be discarded.

    4. Step-by-Step Process
    Receive the keywords in [definition_info].
    Search the two allowed websites using the provided keywords.
    Filter by Publication Date: Discard any search results published more than 7 days ago.
    Analyze Content & Filter Further: For the remaining articles, perform a detailed content analysis to ensure they meet the following criteria:
    Is it a news report? (Per the Article Type Constraint). Discard if it is opinion or commentary.
    Are the events recent? (Per the Dual Recency Constraint). Discard if it discusses events older than 7 days.
    Is it relevant? (Per the Relevance Constraint). Discard if the keywords are not used in a meaningful context.
    VERIFY URL: For each article that has passed all previous checks, actively check its URL to confirm it is accessible and does not return an error (e.g., 404). Discard any article with a broken or inaccessible link.
    Extract Content: For the articles that have passed all checks, extract the required information and summarize the content into 2-3 paragraphs.
    Format Output: Format the extracted information for 2 to 3 valid articles precisely according to the Output Format specification.
    5. Output Format
    Your response must contain ONLY the formatted output for the articles.
    Do not include any introductory text, closing remarks, apologies, or explanations.
    For each article, you must provide the following information in this exact Markdown format:
    -----------------------------------------------------------------------------------------------------------------------------------------------
    Article 1:

    Title: [Exact Title of the Article]
    Publication Date: [YYYY-MM-DD]
    Summary: [A summary (2-3 paragraphs) that explicitly states which keyword(s) from [definition_info] were found and explains their context in the article, focusing on the recent events described.]
    URL: [Full, Direct, and Verified Accessible URL]
    -----------------------------------------------------------------------------------------------------------------------------------------------
    Article 2:

    Title: [Exact Title of the Article]
    Publication Date: [YYYY-MM-DD]
    Summary: [A summary (2-3 paragraphs) that explicitly states which keyword(s) from [definition_info] were found and explains their context in the article, focusing on the recent events described.]
    URL: [Full, Direct, and Verified Accessible URL]
    (Repeat for up to 3 articles)
 
 
    """,
 
    tools=[google_search],
 
    output_key="news_info_genA",
 
     after_model_callback=after_model_callback,
 
)
 
 
 
 
