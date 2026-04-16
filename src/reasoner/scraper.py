"""
Reasoner - Web Scraper Module
Provides deep reading capabilities to fetch full page content and convert to markdown.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Simple HTML to Markdown conversion (lightweight alternative to turndown)
HTML_TAGS_TO_MARKDOWN = {
    '<h1>': '# ',
    '</h1>': '\n',
    '<h2>': '## ',
    '</h2>': '\n',
    '<h3>': '### ',
    '</h3>': '\n',
    '<h4>': '#### ',
    '</h4>': '\n',
    '<h5>': '##### ',
    '</h5>': '\n',
    '<h6>': '###### ',
    '</h6>': '\n',
    '<p>': '',
    '</p>': '\n\n',
    '<br>': '\n',
    '<br/>': '\n',
    '<br />': '\n',
    '<strong>': '**',
    '</strong>': '**',
    '<b>': '**',
    '</b>': '**',
    '<em>': '*',
    '</em>': '*',
    '<i>': '*',
    '</i>': '*',
    '<code>': '`',
    '</code>': '`',
    '<pre>': '```\n',
    '</pre>': '\n```\n',
    '<blockquote>': '> ',
    '</blockquote>': '\n',
    '<li>': '- ',
    '</li>': '\n',
    '<ul>': '',
    '</ul>': '\n',
    '<ol>': '',
    '</ol>': '\n',
    '<a href="': '[',
    '">': '](',
    '</a>': ')',
    '<img src="': '![',
    '" alt="': '](',
    '">': ')',
}


def _simple_html_to_markdown(html: str) -> str:
    """Simple HTML to Markdown conversion."""
    # Remove script and style tags with their content
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # Basic tag replacements
    for tag, md in HTML_TAGS_TO_MARKDOWN.items():
        html = html.replace(tag, md)
    
    # Remove remaining HTML tags
    html = re.sub(r'<[^>]+>', '', html)
    
    # Decode HTML entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    html = html.replace('&apos;', "'")
    
    # Clean up whitespace
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = html.strip()
    
    return html


async def scrape_url(url: str, max_length: int = 10000) -> dict[str, Any]:
    """
    Fetch a URL and convert its content to markdown.
    
    Args:
        url: The URL to scrape
        max_length: Maximum length of the extracted content
        
    Returns:
        Dictionary with title, url, content (markdown), and success status
    """
    from reasoner.core.constants import TIMEOUTS
    try:
        async with httpx.AsyncClient(timeout=TIMEOUTS.SCRAPER, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            html = response.text
            
            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            
            # Extract meta description as fallback
            if not title:
                desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                title = desc_match.group(1).strip() if desc_match else ""
            
            # Convert to markdown
            markdown_content = _simple_html_to_markdown(html)
            
            # Truncate if too long
            if len(markdown_content) > max_length:
                markdown_content = markdown_content[:max_length] + "\n\n... (truncated)"
            
            return {
                "url": url,
                "title": title,
                "content": markdown_content,
                "success": True,
            }
            
    except httpx.TimeoutException:
        logger.error(f"Timeout scraping {url}")
        return {"url": url, "title": "", "content": "", "success": False, "error": "Timeout"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error scraping {url}: {e}")
        return {"url": url, "title": "", "content": "", "success": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {"url": url, "title": "", "content": "", "success": False, "error": str(e)}


async def scrape_urls(urls: list[str], max_length: int = 10000) -> list[dict[str, Any]]:
    """
    Scrape multiple URLs concurrently.
    
    Args:
        urls: List of URLs to scrape
        max_length: Maximum length of each extracted content
        
    Returns:
        List of result dictionaries
    """
    tasks = [scrape_url(url, max_length) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions that weren't caught
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "url": urls[i],
                "title": "",
                "content": "",
                "success": False,
                "error": str(result),
            })
        else:
            processed_results.append(result)
    
    return processed_results


# Need to import asyncio for the gather function
import asyncio