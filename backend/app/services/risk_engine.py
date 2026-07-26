from typing import Optional, Dict, Any
from dataclasses import dataclass
from backend.app.AI.classifier import classifier
from backend.app.utils.text_cleaner import clean_html_content
from backend.app.services.redirect_engine import RedirectEvaluationResult
from backend.app.utils.logger import logger

@dataclass
class DualRiskEvaluationResult:
    final_risk_score: int
    primary_category: str
    category_confidence: float
    summary: str
    original_category: str
    original_risk: int
    redirect_target_category: Optional[str] = None
    redirect_target_risk: int = 0
    risk_narrative: Optional[str] = None
    category_scores: Dict[str, float] = None


class RiskDecisionEngine:
    @staticmethod
    def evaluate_dual_risk(
        original_html: str,
        target_html: Optional[str],
        redirect_eval: RedirectEvaluationResult,
        domain: str
    ) -> DualRiskEvaluationResult:
        """
        Runs independent ML classification on original snapshot HTML and target HTML,
        and applies the Dual Risk Matrix.
        """
        # 1. Clean & Classify Original Snapshot
        orig_cleaned = clean_html_content(original_html or "")
        orig_clf = classifier.classify_snapshot(orig_cleaned)

        orig_category = orig_clf.primary_category
        orig_confidence = orig_clf.confidence
        orig_scores = orig_clf.all_scores
        orig_risk = int(round(orig_scores.get(orig_category, 0.0) * 100)) if orig_scores else 0

        # Adjust base original risk for high-severity categories
        if orig_category in ("gambling", "adult", "phishing", "malware"):
            orig_risk = max(orig_risk, 80)
        elif orig_category in ("crypto", "financial_scam"):
            orig_risk = max(orig_risk, 65)

        target_category: Optional[str] = None
        target_risk: int = 0
        target_clf = None

        # 2. Clean & Classify Target HTML if redirect detected & target HTML available
        if redirect_eval.redirect_detected and target_html:
            target_cleaned = clean_html_content(target_html)
            target_clf = classifier.classify_snapshot(target_cleaned)
            target_category = target_clf.primary_category
            t_scores = target_clf.all_scores
            target_risk = int(round(t_scores.get(target_category, 0.0) * 100)) if t_scores else 0
            if target_category in ("gambling", "adult", "phishing", "malware"):
                target_risk = max(target_risk, 85)

        # 3. Apply Dual Risk Matrix
        final_risk = orig_risk
        display_category = orig_category
        narrative: Optional[str] = None
        final_confidence = orig_confidence
        final_summary = orig_clf.summary

        if redirect_eval.redirect_detected:
            if target_category in ("gambling", "adult", "phishing", "malware"):
                final_risk = max(orig_risk, target_risk, 85)
                display_category = f"{orig_category} -> {target_category}"
                narrative = (
                    f"⚠️ CHRONOSENTINEL WARNING: Snapshot for {domain} redirects to an external "
                    f"{target_category.upper()} threat network ({redirect_eval.redirect_target}). "
                    f"Original page was classified as '{orig_category}'."
                )
                if target_clf:
                    final_confidence = target_clf.confidence
                    final_summary = target_clf.summary
            elif target_category and target_category != "safe":
                final_risk = max(orig_risk, target_risk, 50)
                display_category = f"{orig_category} -> {target_category}"
                narrative = f"Snapshot redirects to external {target_category} site ({redirect_eval.redirect_target})."

        return DualRiskEvaluationResult(
            final_risk_score=final_risk,
            primary_category=display_category,
            category_confidence=final_confidence,
            summary=final_summary,
            original_category=orig_category,
            original_risk=orig_risk,
            redirect_target_category=target_category,
            redirect_target_risk=target_risk,
            risk_narrative=narrative,
            category_scores=orig_scores
        )
