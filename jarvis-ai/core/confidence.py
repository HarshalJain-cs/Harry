"""
JARVIS Confidence Scoring - Execution gating based on confidence levels.

Determines whether to execute, confirm, or refuse actions based on
confidence scores and risk assessment.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class ExecutionMode(Enum):
    """Execution decision modes."""
    EXECUTE = "execute"    # High confidence - execute immediately
    CONFIRM = "confirm"    # Medium confidence - ask for confirmation
    REFUSE = "refuse"      # Low confidence - don't execute


@dataclass
class ConfidenceResult:
    """Result of confidence scoring."""
    score: float
    mode: ExecutionMode
    reasoning: str
    risk_level: str = "low"
    requires_confirmation: bool = False


class ConfidenceScorer:
    """
    Score confidence and determine execution mode.
    
    Uses thresholds to decide whether to:
    - Execute immediately (high confidence)
    - Ask for confirmation (medium confidence)  
    - Refuse execution (low confidence)
    
    Risk levels modify the effective confidence score.
    """
    
    DEFAULT_THRESHOLDS = {
        "execute": 0.85,  # Above this = auto-execute
        "confirm": 0.60,  # Above this = ask confirmation
        # Below confirm threshold = refuse
    }
    
    DEFAULT_RISK_WEIGHTS = {
        "low": 1.0,      # No penalty
        "medium": 0.85,  # 15% penalty
        "high": 0.70,    # 30% penalty
    }
    
    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        risk_weights: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize confidence scorer.
        
        Args:
            thresholds: Custom threshold values
            risk_weights: Custom risk weight multipliers
        """
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        self.risk_weights = risk_weights or self.DEFAULT_RISK_WEIGHTS.copy()
    
    def score(
        self,
        intent_confidence: float,
        tool_risk: str = "low",
        context_factors: Optional[Dict[str, float]] = None,
    ) -> ConfidenceResult:
        """
        Calculate confidence score and execution mode.
        
        Args:
            intent_confidence: Raw confidence from intent parsing (0.0-1.0)
            tool_risk: Risk level of the tool ("low", "medium", "high")
            context_factors: Additional factors affecting confidence
            
        Returns:
            ConfidenceResult with score and execution decision
        """
        # Clamp input confidence
        base_confidence = max(0.0, min(1.0, intent_confidence))
        
        # Apply risk weight
        risk_weight = self.risk_weights.get(tool_risk, 1.0)
        adjusted_score = base_confidence * risk_weight
        
        # Apply context factors if provided
        if context_factors:
            for factor, weight in context_factors.items():
                adjusted_score *= weight
        
        # Clamp final score
        adjusted_score = max(0.0, min(1.0, adjusted_score))
        
        # Determine execution mode
        if adjusted_score >= self.thresholds["execute"]:
            mode = ExecutionMode.EXECUTE
            reasoning = f"High confidence ({adjusted_score:.2f}) - executing automatically"
            requires_confirmation = False
        
        elif adjusted_score >= self.thresholds["confirm"]:
            mode = ExecutionMode.CONFIRM
            reasoning = f"Medium confidence ({adjusted_score:.2f}) - requesting confirmation"
            requires_confirmation = True
        
        else:
            mode = ExecutionMode.REFUSE
            reasoning = f"Low confidence ({adjusted_score:.2f}) - refusing execution"
            requires_confirmation = False
        
        return ConfidenceResult(
            score=adjusted_score,
            mode=mode,
            reasoning=reasoning,
            risk_level=tool_risk,
            requires_confirmation=requires_confirmation,
        )
    
    def score_intent(
        self,
        parsed_intent: Dict[str, Any],
        tool_risk: str = "low",
    ) -> ConfidenceResult:
        """
        Score confidence from a parsed intent dictionary.
        
        Args:
            parsed_intent: Dict with 'confidence' key
            tool_risk: Risk level of the associated tool
            
        Returns:
            ConfidenceResult with score and decision
        """
        confidence = parsed_intent.get("confidence", 0.5)
        return self.score(confidence, tool_risk)
    
    def should_execute(self, confidence_result: ConfidenceResult) -> bool:
        """Check if result indicates immediate execution."""
        return confidence_result.mode == ExecutionMode.EXECUTE
    
    def should_confirm(self, confidence_result: ConfidenceResult) -> bool:
        """Check if result requires confirmation."""
        return confidence_result.mode == ExecutionMode.CONFIRM
    
    def should_refuse(self, confidence_result: ConfidenceResult) -> bool:
        """Check if result indicates refusal."""
        return confidence_result.mode == ExecutionMode.REFUSE
    
    def adjust_thresholds(self, execute: float = None, confirm: float = None):
        """Adjust scoring thresholds."""
        if execute is not None:
            self.thresholds["execute"] = max(0.0, min(1.0, execute))
        if confirm is not None:
            self.thresholds["confirm"] = max(0.0, min(1.0, confirm))
    
    def get_mode_for_action(
        self,
        action_type: str,
        confidence: float,
    ) -> ExecutionMode:
        """
        Get execution mode for a specific action type.
        
        Some actions have built-in risk levels.
        """
        # Built-in risk mappings
        high_risk_actions = {
            "delete_file", "format_disk", "run_as_admin",
            "modify_registry", "uninstall_app",
        }
        
        medium_risk_actions = {
            "close_app", "run_command", "modify_file",
            "send_email", "post_message",
        }
        
        if action_type in high_risk_actions:
            risk = "high"
        elif action_type in medium_risk_actions:
            risk = "medium"
        else:
            risk = "low"
        
        result = self.score(confidence, risk)
        return result.mode


if __name__ == "__main__":
    # Test confidence scorer
    print("Testing Confidence Scorer...")
    
    scorer = ConfidenceScorer()
    
    test_cases = [
        {"confidence": 0.95, "risk": "low", "desc": "High conf, low risk"},
        {"confidence": 0.75, "risk": "low", "desc": "Medium conf, low risk"},
        {"confidence": 0.40, "risk": "low", "desc": "Low conf, low risk"},
        {"confidence": 0.90, "risk": "high", "desc": "High conf, high risk"},
        {"confidence": 0.75, "risk": "high", "desc": "Medium conf, high risk"},
    ]
    
    for case in test_cases:
        result = scorer.score(case["confidence"], case["risk"])
        print(f"\n{case['desc']}:")
        print(f"  Input: conf={case['confidence']}, risk={case['risk']}")
        print(f"  Score: {result.score:.3f}")
        print(f"  Mode: {result.mode.value}")
        print(f"  {result.reasoning}")
