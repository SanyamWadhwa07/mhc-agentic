"""
Session analyzer - View conversation history and assessment results.
"""
import json
import os
from datetime import datetime


def list_sessions():
    """List all available sessions."""
    if not os.path.exists('sessions'):
        print("No sessions found.")
        return []
    
    sessions = []
    for file in os.listdir('sessions'):
        if file.endswith('.json') and not file.endswith('_assessment.json'):
            session_id = file.replace('.json', '')
            sessions.append(session_id)
    
    return sessions


def view_session(session_id: str):
    """View detailed session information."""
    session_file = f'sessions/{session_id}.json'
    assessment_file = f'sessions/{session_id}_assessment.json'
    
    if not os.path.exists(session_file):
        print(f"Session {session_id} not found.")
        return
    
    # Load session data
    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    print("=" * 80)
    print(f"SESSION: {session_id}")
    print("=" * 80)
    print(f"Messages: {session_data['message_count']}")
    print(f"Last Updated: {session_data['last_updated']}")
    print()
    
    # Show summaries
    if session_data.get('summaries'):
        print("CONVERSATION SUMMARIES")
        print("-" * 80)
        for i, summary in enumerate(session_data['summaries'], 1):
            print(f"\nSummary {i} (Messages {summary['message_range']}):")
            print(f"{summary['summary']}")
        print()
    
    # Show recent messages
    print("RECENT MESSAGES")
    print("-" * 80)
    messages = session_data['messages'][-10:]  # Last 10 messages
    for msg in messages:
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {msg['role']}:")
        print(f"{msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")
    
    # Load assessment data if available
    if os.path.exists(assessment_file):
        with open(assessment_file, 'r', encoding='utf-8') as f:
            assessment_data = json.load(f)
        
        print("\n" + "=" * 80)
        print("PSYCHOLOGICAL ASSESSMENT")
        print("=" * 80)
        
        scores = assessment_data.get('scores', {})
        print(f"\nEstimated PHQ-9 (Depression): {scores.get('phq9_estimated', 0)}/27")
        print(f"Estimated GAD-7 (Anxiety): {scores.get('gad7_estimated', 0)}/21")
        print(f"Risk Level: {scores.get('risk_level', 'unknown').upper()}")
        
        if scores.get('concerns'):
            print("\nKey Concerns:")
            for concern in scores['concerns']:
                print(f"  • {concern}")
        
        responses = assessment_data.get('responses', {})
        if responses:
            print(f"\nSymptoms Detected: {', '.join(responses.keys())}")
            print(f"Total Symptom Mentions: {sum(len(v) for v in responses.values())}")
    
    print("\n" + "=" * 80)


def main():
    """Interactive session viewer."""
    sessions = list_sessions()
    
    if not sessions:
        return
    
    print("Available Sessions:")
    print("-" * 40)
    for i, session_id in enumerate(sessions, 1):
        print(f"{i}. {session_id}")
    
    print("\nEnter session number to view details (or 'q' to quit):")
    choice = input("> ").strip()
    
    if choice.lower() == 'q':
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            view_session(sessions[idx])
        else:
            print("Invalid session number.")
    except ValueError:
        print("Invalid input.")


if __name__ == '__main__':
    main()
