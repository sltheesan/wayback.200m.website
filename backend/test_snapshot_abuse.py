import pytest
from backend.app.services.snapshot_evidence import (
    extract_original_url,
    extract_domain_from_url,
    is_external_domain,
    analyze_snapshot_evidence
)
from backend.app.services.analyzer import analyze_snapshot_content
from backend.app.services.risk_engine import compute_overall_risk

def test_extract_original_url():
    wayback_url = "https://web.archive.org/web/20260518022104id_/http://example.com/page"
    cleaned = extract_original_url(wayback_url)
    assert cleaned == "http://example.com/page"
    assert extract_domain_from_url(cleaned) == "example.com"

def test_external_domain_check():
    assert is_external_domain("casino.com", "example.com") is True
    assert is_external_domain("sub.example.com", "example.com") is False
    assert is_external_domain("web.archive.org", "example.com") is False

def test_snapshot_evidence_analyzer_gambling_script_and_backlinks():
    html_content = """
    <html>
    <head>
        <script src="https://web.archive.org/web/20260518022104id_/https://mlbetjs.com/js/file.js"></script>
    </head>
    <body>
        <h1>Welcome to Wexford Townhomes</h1>
        <a href="https://web.archive.org/web/20260518022104id_/http://casino-example.com">开云体育</a>
        <a href="http://gambling-bet.com">江南买球</a>
        <a href="http://slot777.com">百家乐</a>
    </body>
    </html>
    """
    domain = "liveatwexfordtownhomes.com"
    score, findings, telemetry = analyze_snapshot_evidence(html_content, domain)
    
    assert score >= 70
    assert telemetry["findings_count"] >= 3
    
    finding_types = [f["finding_type"] for f in findings]
    assert "external_script" in finding_types or "suspicious_script" in finding_types
    assert "external_link" in finding_types

def test_historical_abuse_domain_classification():
    # Simulate snapshot history where an old 2022 snapshot had a high abuse score (90)
    # but the 2026 snapshot score is 0
    snapshots_risk = [
        {"timestamp": "20180101", "risk_score": 0},
        {"timestamp": "20220518", "risk_score": 90},
        {"timestamp": "20260518", "risk_score": 0}
    ]
    
    overall_score, overall_level, peak_score, avg_score = compute_overall_risk(snapshots_risk)
    
    assert peak_score == 90
    assert overall_score >= 70
    assert overall_level == "HIGH"

def test_safe_domain_with_normal_external_links():
    # Page with 13 standard external links (social media, partners, references)
    html_content = """
    <html>
    <body>
        <h1>Legitimate Business Site</h1>
        <p>Contact us on social media:</p>
        <a href="https://twitter.com/business">Twitter</a>
        <a href="https://facebook.com/business">Facebook</a>
        <a href="https://linkedin.com/company/business">LinkedIn</a>
        <a href="https://instagram.com/business">Instagram</a>
        <a href="https://youtube.com/user/business">YouTube</a>
        <a href="https://github.com/business">GitHub</a>
        <a href="https://google.com">Google</a>
        <a href="https://apple.com">Apple</a>
        <a href="https://microsoft.com">Microsoft</a>
        <a href="https://wikipedia.org/wiki/Business">Wikipedia</a>
        <a href="https://w3.org">W3C</a>
        <a href="https://schema.org">Schema</a>
        <a href="https://wordpress.org">WordPress</a>
    </body>
    </html>
    """
    domain = "legitimate-business-site.com"
    score, findings, telemetry = analyze_snapshot_evidence(html_content, domain)
    
    assert score == 0
    assert len(findings) == 0
    assert telemetry["external_links_count"] == 13

def test_redirect_snapshot_forces_unsafe_domain():
    # Domain with historical snapshot redirect
    snapshots_risk = [
        {"timestamp": "20180101", "risk_score": 0, "is_redirect": False},
        {"timestamp": "20220518", "risk_score": 0, "is_redirect": True, "redirect_url": "https://casino.com"},
        {"timestamp": "20260518", "risk_score": 0, "is_redirect": False}
    ]
    
    overall_score, overall_level, peak_score, avg_score = compute_overall_risk(snapshots_risk)
    
    assert overall_score >= 85
    assert overall_level == "HIGH"

if __name__ == "__main__":
    test_extract_original_url()
    test_external_domain_check()
    test_snapshot_evidence_analyzer_gambling_script_and_backlinks()
    test_historical_abuse_domain_classification()
    test_safe_domain_with_normal_external_links()
    test_redirect_snapshot_forces_unsafe_domain()
    print("ALL HISTORICAL SNAPSHOT ABUSE TESTS PASSED SUCCESSFULLY!")
