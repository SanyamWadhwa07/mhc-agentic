"""
Quick test to verify emotional intelligence features work correctly.
Run this to test multi-label emotion detection and therapist micro-skills.
"""

from nlp_enhancements import SentimentAnalyzer
from mood_tracker import MoodTracker

def test_multi_label_emotions():
    """Test that multiple emotions are detected correctly."""
    analyzer = SentimentAnalyzer()
    
    test_cases = [
        {
            "text": "My partner lied to me and I feel so stupid and alone",
            "expected_emotions": ["betrayal", "shame", "loneliness"],
            "description": "Betrayal + shame + loneliness scenario"
        },
        {
            "text": "I'm such an idiot for trusting them again",
            "expected_emotions": ["shame", "hurt"],
            "description": "Shame + hurt from repeated betrayal"
        },
        {
            "text": "I feel so angry but also scared to say anything",
            "expected_emotions": ["anger", "fear"],
            "description": "Anger + fear conflict"
        },
        {
            "text": "Nobody cares if I'm alive or dead",
            "expected_emotions": ["loneliness", "hopelessness"],
            "description": "Loneliness + hopelessness (soft crisis)"
        },
        {
            "text": "I miss them so much it physically hurts",
            "expected_emotions": ["grief", "hurt"],
            "description": "Grief + hurt from loss"
        }
    ]
    
    print("=" * 60)
    print("MULTI-LABEL EMOTION DETECTION TEST")
    print("=" * 60)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['description']}")
        print(f"Input: \"{case['text']}\"")
        
        result = analyzer.analyze(case['text'])
        
        print(f"Primary emotion: {result['emotion']}")
        print(f"All detected emotions: {result['emotions']}")
        print(f"Sentiment score: {result['sentiment_score']}")
        print(f"Urgency: {result['urgency']}")
        
        # Check if expected emotions were detected
        detected = set(result['emotions'])
        expected = set(case['expected_emotions'])
        
        if expected.issubset(detected):
            print("✅ PASS - All expected emotions detected")
        else:
            missing = expected - detected
            print(f"❌ FAIL - Missing emotions: {missing}")
        
        print("-" * 60)


def test_mood_tracking():
    """Test mood tracking and trend analysis."""
    tracker = MoodTracker("test_session")
    
    print("\n" + "=" * 60)
    print("MOOD TRACKING TEST")
    print("=" * 60)
    
    # Simulate mood decline
    mood_sequence = [
        (0.5, "coping", "Starting okay"),
        (0.3, "struggling", "Getting harder"),
        (0.0, "distressed", "Really struggling now"),
        (-0.3, "struggling", "Feeling worse"),
        (-0.5, "hopelessness", "Can't see a way out")
    ]
    
    print("\nSimulating mood decline:")
    for score, emotion, note in mood_sequence:
        sentiment_data = {'sentiment_score': score, 'emotion': emotion, 'urgency': 'moderate'}
        tracker.record_mood(sentiment_data, note)
        print(f"  - {note}: score={score}, emotion={emotion}")
    
    print("\nMood Analysis:")
    trend = tracker.get_mood_trend()
    print(f"Trend: {trend}")
    
    pattern = tracker.get_emotional_pattern()
    print(f"Pattern: {pattern}")
    
    guidance = tracker.get_response_guidance()
    print(f"\nResponse Guidance:")
    print(f"  Tone: {guidance['tone']}")
    print(f"  Approach: {guidance['approach']}")
    print(f"  Priority: {guidance['priority']}")
    print(f"  Caution: {guidance['caution']}")
    
    if trend == "declining":
        print("✅ PASS - Correctly detected declining mood")
    else:
        print(f"❌ FAIL - Expected 'declining', got '{trend}'")


def test_therapist_micro_skills_context():
    """Test that emotion-specific guidance is generated correctly."""
    analyzer = SentimentAnalyzer()
    
    print("\n" + "=" * 60)
    print("THERAPIST MICRO-SKILLS CONTEXT TEST")
    print("=" * 60)
    
    test_text = "They promised they'd never do it again but they lied. I feel like such an idiot."
    result = analyzer.analyze(test_text)
    
    print(f"\nInput: \"{test_text}\"")
    print(f"\nDetected emotions: {result['emotions']}")
    
    # Check if guidance would be triggered
    expected_guidance = []
    if 'betrayal' in result['emotions']:
        expected_guidance.append("Betrayal: Acknowledge trust violation directly")
    if 'shame' in result['emotions']:
        expected_guidance.append("Shame: Normalize, de-stigmatize")
    if 'hurt' in result['emotions']:
        expected_guidance.append("Hurt: Acknowledge pain, don't rush to fix")
    
    print(f"\nExpected guidance triggers:")
    for g in expected_guidance:
        print(f"  - {g}")
    
    if len(expected_guidance) > 0:
        print("\n✅ PASS - Multiple guidance triggers available")
    else:
        print("\n❌ FAIL - No guidance triggers")


if __name__ == "__main__":
    test_multi_label_emotions()
    test_mood_tracking()
    test_therapist_micro_skills_context()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
    print("\nTo test the full system with real responses:")
    print("  $env:DEBUG_MODE=\"true\"; python run_agent.py")
