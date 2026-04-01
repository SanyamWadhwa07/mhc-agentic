import pytest
from app.safety.crisis_detector import CrisisDetector

detector = CrisisDetector()


@pytest.mark.parametrize("message", [
    "marna chahta hoon",
    "khatam kar loon apne aap ko",
    "jeena nahi chahti",
    "suicide karna chahta hoon",
    "bas sab khatam ho jaye",
    "bina mujhare sab theek rahenge",
    "want to die",
    "kill myself",
])
def test_hard_crisis_detected(message):
    assert detector.is_hard_crisis(message), f"Failed to detect: {message}"


@pytest.mark.parametrize("message", [
    "main theek hoon",
    "aaj bahut acha din tha",
    "kya tum mera homework kar sakte ho",
    "kamarna chahta hoon",  # "marna" inside "kamarna" must NOT trigger
])
def test_no_false_positives(message):
    assert not detector.is_hard_crisis(message), f"False positive: {message}"
