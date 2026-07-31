import re
from typing import Dict, List, Any, Tuple, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from backend.app.services.analyzer import LANGUAGE_KEYWORDS, keyword_match_count
from backend.app.utils.logger import logger

def extract_original_url(url: str) -> str:
    """
    Unwraps Wayback Machine archive wrappers from a URL.
    Example input: https://web.archive.org/web/20260518022104id_/http://example.com
    Example output: http://example.com
    """
    if not url:
        return ""
    
    clean_url = str(url).strip()
    
    # Handle id_/ wrapper
    if "id_/" in clean_url:
        clean_url = clean_url.split("id_/")[-1]
    
    # Handle /web/TIMESTAMP/ wrapper
    elif "web.archive.org/web/" in clean_url:
        match = re.search(r"web\.archive\.org/web/\d+(?:[a-z_]+)?/(https?://.+)$", clean_url, re.IGNORECASE)
        if match:
            clean_url = match.group(1)
        else:
            parts = clean_url.split("/web/")
            if len(parts) > 1:
                subparts = parts[1].split("/", 2)
                if len(subparts) > 2 and subparts[2].startswith("http"):
                    clean_url = subparts[2]

    # Clean double slashes in protocol if present
    clean_url = re.sub(r"^(https?://)+", r"\1", clean_url, flags=re.IGNORECASE)
    return clean_url

def extract_domain_from_url(url: str) -> str:
    """Extracts bare domain name from any URL (e.g., 'https://sub.example.com/path' -> 'sub.example.com')."""
    if not url:
        return ""
    unwrapped = extract_original_url(url)
    if not unwrapped.startswith("http://") and not unwrapped.startswith("https://"):
        unwrapped = "http://" + unwrapped
    try:
        parsed = urlparse(unwrapped)
        return (parsed.netloc or parsed.path).split(":")[0].lower()
    except Exception:
        return unwrapped.split("/")[0].split(":")[0].lower()

def is_external_domain(target_domain: str, base_domain: str) -> bool:
    """Returns True if target_domain is outside base_domain and not archive.org."""
    if not target_domain or not base_domain:
        return False
        
    t_clean = target_domain.lower().removeprefix("www.")
    b_clean = base_domain.lower().removeprefix("www.")
    
    if "web.archive.org" in t_clean or "archive.org" in t_clean:
        return False
        
    if t_clean == b_clean or t_clean.endswith("." + b_clean) or b_clean.endswith("." + t_clean):
        return False
        
    return True

# Comprehensive Gambling & Adult Anchor/Domain Keywords (Multilingual Chinese + English)
THREAT_KEYWORDS = {
    "gambling": [
        "casino", "bet", "poker", "slots", "sportsbook", "baccarat", "wager", "jackpot", "bookie",
        "roulette", "blackjack", "slotgacor", "judi", "situs slot", "situs judi",
        "博彩", "买球", "下注", "百家乐", "赌场", "体育", "彩票", "江南买球", "开云体育", "皇冠现金网",
        "在线赌场", "真人娱乐", "六合彩", "棋牌", "斗地主", "返水", "捕鱼达人", "赔率", "盘口", "太阳城", "威尼斯人", "金沙"
    ],
    "adult": [
        "xxx", "porn", "adult", "sex", "nude", "escort", "erotic", "hentai", "pornhub", "xvideos",
        "onlyfans", "nsfw", "camgirl", "色情", "成人", "无码", "有码", "日本无码", "精品在线", "国产精品",
        "人妻", "日韩", "欧美", "黄片", "一本道", "东京热", "加勒比", "巨乳", "乱伦"
    ],
    "scam_phishing": [
        "crypto scam", "fake-login", "giveaway", "free-money", "verify-account", "claim-bonus",
        "刷单", "兼职", "套利", "高收益", "保本", "漏洞"
    ]
}

def analyze_snapshot_evidence(
    html_content: str,
    domain: str,
    redirect_target: Optional[str] = None
) -> Tuple[int, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Analyzes snapshot HTML for external link abuse, script injections,
    suspicious anchor texts, SEO spam links, and computes snapshot risk score & findings.
    
    Returns:
      (snapshot_risk_score, list_of_findings, summary_telemetry)
    """
    if not html_content and not redirect_target:
        return 0, [], {}

    findings: List[Dict[str, Any]] = []
    base_domain = extract_domain_from_url(domain) if domain else ""
    
    external_links: List[Dict[str, str]] = []
    external_scripts: List[str] = []
    
    try:
        soup = BeautifulSoup(html_content or "", "html.parser")
    except Exception:
        soup = None

    if soup:
        # 1. Extract External Links & Anchors
        for a_tag in soup.find_all("a", href=True):
            raw_href = a_tag["href"]
            original_href = extract_original_url(raw_href)
            target_dom = extract_domain_from_url(original_href)
            
            if is_external_domain(target_dom, base_domain):
                anchor_text = a_tag.get_text(strip=True)
                external_links.append({
                    "href": original_href,
                    "domain": target_dom,
                    "anchor": anchor_text
                })

        # 2. Extract External JavaScript Sources
        for script_tag in soup.find_all("script", src=True):
            raw_src = script_tag["src"]
            original_src = extract_original_url(raw_src)
            script_dom = extract_domain_from_url(original_src)
            if is_external_domain(script_dom, base_domain):
                external_scripts.append(original_src)

    # 3. Analyze External Scripts for Threat Signals
    script_risk_score = 0
    for script_url in external_scripts:
        script_lower = script_url.lower()
        script_dom = extract_domain_from_url(script_url)
        
        # Check script URL against threat keywords
        matched_cat = None
        matched_kw = None
        for category, kws in THREAT_KEYWORDS.items():
            for kw in kws:
                if kw in script_lower:
                    matched_cat = category
                    matched_kw = kw
                    break
            if matched_cat:
                break
                
        if matched_cat:
            findings.append({
                "finding_type": "external_script",
                "evidence": script_dom or script_url,
                "category": matched_cat.capitalize(),
                "risk_score": 70,
                "description": f"External {matched_cat} script injected: {script_url} (Keyword: '{matched_kw}')"
            })
            script_risk_score = max(script_risk_score, 70)
        elif any(sig in script_lower for sig in ["js", "cdn", "api"]) and len(script_dom) > 4:
            # Check for suspicious unknown external script domain
            if any(term in script_lower for term in ["bet", "casino", "game", "slot", "live", "pay"]):
                findings.append({
                    "finding_type": "suspicious_script",
                    "evidence": script_dom,
                    "category": "Gambling",
                    "risk_score": 65,
                    "description": f"Suspicious gambling/gaming script host detected: {script_dom}"
                })
                script_risk_score = max(script_risk_score, 65)

    # 4. Analyze External Links and Anchors
    link_threat_count = 0
    link_risk_score = 0
    
    for link in external_links:
        href_lower = link["href"].lower()
        anchor_lower = link["anchor"].lower()
        combined_link_text = f"{href_lower} {anchor_lower}"
        
        matched_cat = None
        matched_kw = None
        
        for category, kws in THREAT_KEYWORDS.items():
            for kw in kws:
                if kw in combined_link_text:
                    matched_cat = category
                    matched_kw = kw
                    break
            if matched_cat:
                break
                
        if matched_cat:
            link_threat_count += 1
            cat_display = "Gambling" if matched_cat == "gambling" else ("Adult" if matched_cat == "adult" else "Scam/Phishing")
            findings.append({
                "finding_type": "external_link",
                "evidence": f"{link['domain']} (Anchor: '{link['anchor']}')" if link['anchor'] else link['domain'],
                "category": cat_display,
                "risk_score": 60,
                "description": f"External threat backlink to '{link['domain']}' with anchor '{link['anchor']}' (Keyword: '{matched_kw}')"
            })
            link_risk_score = max(link_risk_score, 60)

    # List of common benign social media, tech, and reference domains
    BENIGN_DOMAINS = {
        "twitter.com", "x.com", "facebook.com", "linkedin.com", "instagram.com",
        "youtube.com", "github.com", "wikipedia.org", "google.com", "apple.com",
        "microsoft.com", "schema.org", "w3.org", "wordpress.org", "vimeo.com"
    }

    # Filter out benign external links for spam evaluation
    suspicious_ext_links = [
        link for link in external_links
        if not any(b_dom in link["domain"] for b_dom in BENIGN_DOMAINS)
    ]

    total_ext_links = len(external_links)
    total_suspicious_ext_links = len(suspicious_ext_links)

    # 5. Context-Aware SEO Link Spam Detection Rule
    # Requires high volume of non-benign external links AND presence of threat backlinks
    is_link_spam = (
        (total_suspicious_ext_links >= 30 and link_threat_count >= 2) or
        (total_suspicious_ext_links >= 40 and link_threat_count >= 1)
    )

    if is_link_spam:
        findings.append({
            "finding_type": "link_spam",
            "evidence": f"{total_ext_links} external links ({link_threat_count} threat links)",
            "category": "SEO Spam",
            "risk_score": 35,
            "description": f"Suspicious SEO link spam detected: page contains {total_suspicious_ext_links} non-benign external links and {link_threat_count} threat backlinks."
        })
        link_risk_score = max(link_risk_score, 35)

    # 6. Redirect Target Threat Evaluation
    redirect_risk_score = 0
    if redirect_target:
        red_url = extract_original_url(redirect_target)
        red_dom = extract_domain_from_url(red_url)
        red_lower = red_url.lower()
        
        matched_cat = None
        for category, kws in THREAT_KEYWORDS.items():
            for kw in kws:
                if kw in red_lower:
                    matched_cat = category
                    break
            if matched_cat:
                break
                
        if matched_cat:
            cat_display = "Gambling" if matched_cat == "gambling" else ("Adult" if matched_cat == "adult" else "Scam/Phishing")
            findings.append({
                "finding_type": "redirect_abuse",
                "evidence": red_dom or red_url,
                "category": cat_display,
                "risk_score": 90,
                "description": f"Snapshot redirects directly to external {cat_display} domain: {red_dom}"
            })
            redirect_risk_score = 90

    # 7. Aggregate Total Snapshot Risk Score
    if findings:
        max_finding_score = max((f["risk_score"] for f in findings), default=0)
        total_snapshot_score = max_finding_score
        if len(findings) > 1:
            total_snapshot_score = min(100, max_finding_score + (len(findings) - 1) * 10)
    else:
        total_snapshot_score = 0

    telemetry = {
        "external_links_count": total_ext_links,
        "external_threat_links_count": link_threat_count,
        "external_scripts_count": len(external_scripts),
        "external_scripts": external_scripts[:10],
        "findings_count": len(findings)
    }

    return total_snapshot_score, findings, telemetry
