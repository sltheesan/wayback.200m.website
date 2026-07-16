import re
from html import unescape
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup


HIGH_SIGNAL_ATTRIBUTES = (
    "alt",
    "title",
    "aria-label",
    "content",
    "href",
    "src",
    "data-src",
    "poster",
)

LEETSPEAK_TRANSLATION = str.maketrans({
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
    "!": "i",
})


def _tokenise_attribute_value(value: str) -> str:
    """Turn URLs/filenames/attribute values into words useful for keyword scans."""
    if not value:
        return ""

    value = unescape(unquote(str(value)))
    parsed = urlparse(value)
    parts = [parsed.netloc, parsed.path, parsed.query] if parsed.scheme else [value]
    text = " ".join(part for part in parts if part)
    text = re.sub(r"[_./?&#=:+%~-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_obfuscated_text(text: str) -> str:
    """
    Adds a conservative de-obfuscated view of text for keyword matching.

    The original text is kept by callers; this catches common evasions like
    c4sino, p0rn, b3tting, and crypt0 without replacing the source evidence.
    """
    if not text:
        return ""

    # Convert leetspeak translation first
    normalized = text.lower().translate(LEETSPEAK_TRANSLATION)
    
    # Strip symbols placed between alphanumeric characters (e.g. c*a*s*i*n*o -> casino)
    normalized = re.sub(r"(?<=\w)[._\-*|/\\~](?=\w)", "", normalized)
    
    # De-obfuscate spaced letters (e.g. c a s i n o -> casino, p o r n -> porn)
    # This finds sequences of single characters separated by spaces and combines them
    normalized = re.sub(r"(?:^|(?<=\s))([a-z0-9])(?:\s+([a-z0-9]))+(?=\s|$)", lambda m: m.group(0).replace(" ", ""), normalized)
    
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def clean_html_content(html_content: str) -> str:
    """
    Cleans raw HTML by removing scripts, styling, and HTML tags,
    returning a clean text string for keyword analysis.
    """
    if not html_content:
        return ""

    try:
        # Use bs4 with lxml or html.parser to parse the HTML structure
        soup = BeautifulSoup(html_content, "html.parser")

        attribute_text = []
        for tag in soup.find_all(True):
            for attr in HIGH_SIGNAL_ATTRIBUTES:
                value = tag.get(attr)
                if isinstance(value, list):
                    value = " ".join(value)
                if value:
                    attribute_text.append(_tokenise_attribute_value(value))

        # Remove noisy executable/layout tags before extracting visible text.
        # Metadata was captured above so head/meta image hints are not lost.
        for element in soup(["script", "style", "head", "iframe", "noscript", "meta", "link"]):
            element.decompose()

        # Get plain text
        text = soup.get_text(separator=" ")
        if attribute_text:
            text = f"{text} {' '.join(attribute_text)}"

        # Clean up whitespace and collapse extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception:
        # Fallback to a regex tag stripper if BeautifulSoup fails
        clean_re = re.compile('<.*?>')
        text = re.sub(clean_re, ' ', html_content)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def extract_meta_tags_content(html_content: str) -> str:
    """
    Extracts text ONLY from HTML meta tags (their content, name, property, etc.)
    and ignores the body text, links, image attributes, title tags, etc.
    """
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        meta_texts = []
        for meta in soup.find_all("meta"):
            for attr, value in meta.attrs.items():
                if value:
                    if isinstance(value, list):
                        value = " ".join(value)
                    meta_texts.append(_tokenise_attribute_value(value))
        return " ".join(meta_texts)
    except Exception:
        # Fallback regex parsing if BS4 fails
        meta_pattern = re.compile(r'<meta\s+[^>]*>', re.IGNORECASE)
        attr_pattern = re.compile(r'(\b\w+)\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
        meta_texts = []
        for meta_match in meta_pattern.finditer(html_content):
            meta_tag = meta_match.group(0)
            for attr_match in attr_pattern.finditer(meta_tag):
                value = attr_match.group(2)
                if value:
                    meta_texts.append(_tokenise_attribute_value(value))
        return " ".join(meta_texts)
