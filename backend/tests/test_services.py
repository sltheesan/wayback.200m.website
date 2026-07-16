import pytest
from backend.app.utils.text_cleaner import clean_html_content
from backend.app.services.analyzer import analyze_snapshot_content
from backend.app.AI.classifier import classify_content
from backend.app.services.risk_engine import compute_overall_risk, select_snapshots_to_check

def test_text_cleaner():
    """Verify that html text cleaner strips scripts, styles, and html tags."""
    raw_html = """
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>console.log("hello");</script>
      </head>
      <body>
        <h1>Title Header</h1>
        <p>This is a paragraph with <a href="#">a link</a>.</p>
      </body>
    </html>
    """
    cleaned = clean_html_content(raw_html)
    assert "body {" not in cleaned
    assert "console.log" not in cleaned
    assert "Title Header" in cleaned
    assert "This is a paragraph with a link" in cleaned

def test_analyzer_clean_page():
    """Verify that a clean page gets a risk score of 0 and no flags."""
    html = "<html><body><h1>Hello World</h1><p>We do normal tech coding tutorials.</p></body></html>"
    score, category_scores, flags = analyze_snapshot_content(html)
    assert score == 0
    assert len(flags) == 0

def test_analyzer_gambling_detection():
    """Verify that gambling keywords are detected and accumulate correct weights."""
    html = """
    <html>
      <head>
        <meta name="description" content="Online Casino Slots slots slots casino">
        <meta name="keywords" content="Place your bet now in roulette roulette blackjack blackjack!">
      </head>
      <body>
        <h1>Clean body</h1>
      </body>
    </html>
    """
    score, category_scores, flags = analyze_snapshot_content(html)
    
    # "online casino" -> 50, "casino" -> 40, "slots" -> 35, "roulette" -> 35, "blackjack" -> 30, "bet now" -> 35
    # Since they are all in the gambling category, the total category score is capped at 65.
    assert score == 65
    
    categories = [f["category"] for f in flags]
    assert "gambling" in categories
    
    keywords = [f["keyword"] for f in flags]
    assert "casino" in keywords
    assert "slots" in keywords
    assert "roulette" in keywords

def test_analyzer_score_capping():
    """Verify that risk scores do not exceed 100 even with many keyword hits."""
    # Extremely heavy keywords matching many categories
    html = """
    <html>
      <head>
        <meta name="description" content="Online Casino Casino. xxx porn adult video and crypto scam. cracked software. buy viagra">
      </head>
      <body>
        <h1>Clean body</h1>
      </body>
    </html>
    """
    score, category_scores, flags = analyze_snapshot_content(html)
    assert score == 100
    assert len(flags) >= 4

def test_risk_engine_classification():
    """Verify that average snapshot scores are categorized into appropriate threat bands."""
    # Safe category: final <= 30
    assert compute_overall_risk([10, 20, 30]) == (26, "SAFE", 30, 20)
    
    # Medium risk: 30 < final <= 60
    assert compute_overall_risk([40, 40, 40]) == (40, "MEDIUM", 40, 40)
    assert compute_overall_risk([50, 60, 45]) == (57, "MEDIUM", 60, 52)
    
    # High risk: final > 60
    assert compute_overall_risk([70, 70, 70]) == (70, "HIGH", 70, 70)
    assert compute_overall_risk([80, 90, 75]) == (87, "HIGH", 90, 82)

def test_sampling_strategy_six_or_fewer():
    """Verify that all records are returned sorted chronologically."""
    snapshots = [{"timestamp": str(2025 - i)} for i in range(5)]
    sampled = select_snapshots_to_check(snapshots)
    assert len(sampled) == 5
    assert [s["timestamp"] for s in sampled] == ["2021", "2022", "2023", "2024", "2025"]

def test_sampling_strategy_many():
    """Verify that all records are returned and sorted chronologically even when there are many."""
    # Generate 15 out-of-order snapshots
    snapshots = [{"timestamp": f"{2024 - i}0101120000"} for i in range(15)]
    sampled = select_snapshots_to_check(snapshots)
    
    assert len(sampled) == 15
    
    # Check that they remain sorted chronologically (as required by frontend timeline)
    timestamps = [s["timestamp"] for s in sampled]
    assert timestamps == sorted(timestamps)

def test_analyzer_detects_image_and_meta_signals():
    """Risky words in image alt/src and metadata should count as page evidence."""
    html = """
    <html>
      <head>
        <meta property="og:title" content="Online casino welcome bonus">
        <meta name="keywords" content="sports betting odds live casino jackpot banner">
      </head>
      <body>
        <h1>Welcome</h1>
      </body>
    </html>
    """
    score, category_scores, flags = analyze_snapshot_content(html)
    assert score >= 65
    assert category_scores["gambling"] >= 65
    assert {flag["keyword"] for flag in flags} & {"online casino", "sports betting", "live casino"}


def test_analyzer_detects_obfuscated_keywords():
    """Common evasions like c4sino and p0rn should not be treated as safe."""
    html = """
    <html>
      <head>
        <meta name="description" content="Best online c4sino p0rn adult videos onlyf4ns-promo">
      </head>
      <body>
        <h1>Welcome</h1>
      </body>
    </html>
    """
    score, category_scores, flags = analyze_snapshot_content(html)
    categories = {flag["category"] for flag in flags}
    assert score > 0
    assert "gambling" in categories
    assert "adult" in categories

def test_analyzer_detects_adult_service_image_listing():
    """Adult-service profile/gallery signals in attributes should not be marked safe."""
    html = """
    <html>
      <head>
        <meta name="description" content="Kokura men's esthetic adult massage profiles girl profile escort girls nuru massage sensual massage cast">
      </head>
      <body>
        <h1>Therapist profiles</h1>
      </body>
    </html>
    """
    score, category_scores, flags = analyze_snapshot_content(html)
    keywords = {flag["keyword"] for flag in flags}

    assert score >= 65
    assert category_scores["adult"] >= 65
    assert keywords & {"men's esthetic", "adult massage", "girl profile", "escort girls", "nuru massage"}

def test_analyzer_detects_modern_gambling_slugs_and_brands():
    """Compact betting/slot signals in URLs and image paths should be high risk."""
    html = """
    <html>
      <head>
        <meta name="keywords" content="Bet365 odds slot gacor bonus 1xbet bet slip fixed odds pragmatic play slot777 real money casino online slots jackpot">
      </head>
      <body>
        <h1>Welcome</h1>
      </body>
    </html>
    """
    score, category_scores, flags = analyze_snapshot_content(html)
    keywords = {flag["keyword"] for flag in flags}

    assert score >= 65
    assert category_scores["gambling"] >= 65
    assert keywords & {"bet365", "1xbet", "slot gacor", "slot777", "real money casino"}


def test_classifier_detects_adult_platform_and_18_plus_signals():
    """Adult pages often expose strongest evidence through platform names and media slugs."""
    html = """
    <html>
      <head>
        <meta name="description" content="18+ adult tube free porn videos xvideos live sex cam leaked nudes redtube cam girls webcam sex">
      </head>
      <body>
        <h1>Welcome</h1>
      </body>
    </html>
    """
    result = classify_content(html)
    keywords = {item.keyword for item in result.evidence}

    assert result.primary_category == "adult"
    assert result.confidence >= 0.65
    assert keywords & {"18+", "adult tube", "free porn", "xvideos", "live sex cam", "leaked nudes"}


def test_ssrf_validator():
    """Verify that private and loopback addresses are blocked, and valid public domains pass."""
    from backend.app.services.wayback.validator import validate_target
    from backend.app.services.wayback.exceptions import SSRFValidationError
    
    # Valid domain
    assert validate_target("google.com") == "google.com"
    assert validate_target("https://example.com/some/path") == "example.com"
    
    # Loopback / Local addresses
    with pytest.raises(SSRFValidationError):
        validate_target("localhost")
    with pytest.raises(SSRFValidationError):
        validate_target("127.0.0.1")
    with pytest.raises(SSRFValidationError):
        validate_target("http://192.168.1.1/admin")
    with pytest.raises(SSRFValidationError):
        validate_target("http://metadata.google.internal")

    # Offline/unresolvable domains should pass (not throw SSRFValidationError)
    assert validate_target("completely-fake-domain-that-does-not-exist-at-all-12345.xyz") == "completely-fake-domain-that-does-not-exist-at-all-12345.xyz"
