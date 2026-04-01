import os
import json
from dotenv import load_dotenv
from llm_clients import GroqClient, GeminiClient
from safety import ImmediateCrisisDetector, ContentModeration, InputSanitizer
from tools import *
from core import Controller, ToolExecutionEngine

def test_pipeline():
    load_dotenv()
    print("Initializing components...")
    
    # Mocks/Real clients
    try:
        llm = GroqClient()
    except:
        print("Warning: Could not init GroqClient, using mock if needed or failing.")
        return

    crisis_detector = ImmediateCrisisDetector()
    content_moderator = ContentModeration()
    input_sanitizer = InputSanitizer()
    
    tool_registry = {
        "EmotionTool": EmotionTool(),
        "SentimentTool": SentimentTool(),
        "MemoryReadTool": MemoryReadTool(llm),
        "PatternDetectorTool": PatternDetectorTool(),
        "InterventionSelectorTool": InterventionSelectorTool(),
        "AssessmentTool": AssessmentTool(),
        "MasterResponderTool": MasterResponderTool(llm)
    }
    
    controller = Controller(llm, tool_registry)
    engine = ToolExecutionEngine(tool_registry)
    
    test_cases = [
        "Hi, how are you?",
        "I feel really hopeless and sad today.",
        "I want to kill myself."
    ]
    
    for user_input in test_cases:
        print(f"\n\n--- Testing: '{user_input}' ---")
        
        # Stage 1
        crisis = crisis_detector.check(user_input)
        if crisis['risk_level'] == 'high':
            print(f"Result: BLOCKED by Crisis Detector ({crisis['crisis_type']})")
            continue
            
        mod = content_moderator.check(user_input)
        if mod['blocked']:
            print("Result: BLOCKED by Content Moderator")
            continue
            
        sanitized = input_sanitizer.sanitize(user_input)
        safe_input = sanitized['safe_input']
        
        # Stage 2
        print("Running Controller...")
        plan = controller.decide(safe_input, crisis['risk_level'], "Session start")
        print(f"Plan: {json.dumps(plan, indent=2)}")
        
        print("Executing Tools...")
        context = {"risk_level": crisis['risk_level'], "session_summary": "Session start"}
        result = engine.execute_plan(plan, safe_input, context)
        
        print(f"Final Response: {result.get('final_response', {}).get('reply_text')}")

if __name__ == "__main__":
    test_pipeline()
