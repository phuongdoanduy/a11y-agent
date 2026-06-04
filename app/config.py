# Copyright 2026 Optimus Team
# MIT License

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

if os.getenv("GOOGLE_API_KEY"):
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")
else:
    import google.auth
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id or "")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


@dataclass
class A11yConfiguration:
    """Configuration for the A11y audit agent system.

    Attributes:
        critic_model: Model for evaluation and report composition.
        worker_model: Model for scanning and analysis tasks.
        max_audit_iterations: Maximum iterative refinement passes.
        compliance_threshold: Minimum score to pass (0-100).
        block_on_critical: Block PR if any critical violation found.
        block_on_regression: Block PR if resolved finding reappears.
        block_on_serious_count: Block PR if serious violations exceed this.
    """

    critic_model: str = "gemini-2.5-pro"
    worker_model: str = "gemini-2.5-pro"
    max_audit_iterations: int = 3
    compliance_threshold: int = 85
    block_on_critical: bool = True
    block_on_regression: bool = True
    block_on_serious_count: int = 5

    # Severity scoring (points deducted per finding)
    severity_scores: dict[str, int] = field(default_factory=lambda: {
        "critical": -10,
        "serious": -5,
        "moderate": -2,
        "minor": -1,
    })

    # WCAG success criteria for AA conformance
    wcag_aa_criteria: list[str] = field(default_factory=lambda: [
        "1.1.1",  # Non-text Content
        "1.2.1",  # Audio-only and Video-only
        "1.3.1",  # Info and Relationships
        "1.3.2",  # Meaningful Sequence
        "1.3.3",  # Sensory Characteristics
        "1.4.1",  # Use of Color
        "1.4.3",  # Contrast (Minimum)
        "1.4.4",  # Resize Text
        "1.4.5",  # Images of Text
        "2.1.1",  # Keyboard
        "2.1.2",  # No Keyboard Trap
        "2.4.1",  # Bypass Blocks
        "2.4.2",  # Page Titled
        "2.4.3",  # Focus Order
        "2.4.4",  # Link Purpose
        "2.4.6",  # Headings and Labels
        "2.4.7",  # Focus Visible
        "3.1.1",  # Language of Page
        "3.1.2",  # Language of Parts
        "3.2.1",  # On Focus
        "3.2.2",  # On Input
        "3.3.1",  # Error Identification
        "3.3.2",  # Labels or Instructions
        "4.1.1",  # Parsing
        "4.1.2",  # Name, Role, Value
    ])


config = A11yConfiguration()
