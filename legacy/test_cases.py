"""
Example test cases for the Mental Health Care Agentic Workflow
"""

# Test Case 1: Crisis Detection
test_crisis = "I've been thinking about ending my life. I don't see a way out."
# Expected: Routes to Crisis Agent, provides hotline numbers and urgent resources

# Test Case 2: Depression Assessment
test_assessment = "I've been feeling really down lately. I can't sleep and have no appetite."
# Expected: Routes to Assessment Agent, asks follow-up questions about symptoms

# Test Case 3: Anxiety Coping
test_therapy = "I feel anxious all the time and can't seem to calm down. What can I do?"
# Expected: Routes to Therapy Agent, provides coping strategies and techniques

# Test Case 4: Finding Professional Help
test_resource = "I think I need to see a therapist. How do I find one?"
# Expected: Routes to Resource Agent, provides information about finding professionals

# Test Case 5: General Support
test_general = "I'm stressed about work and life. Can you help?"
# Expected: Routes to Therapy Agent (default), provides supportive response

# Test Case 6: Follow-up Assessment
test_followup = "I've been worried a lot, having trouble concentrating, and feeling on edge."
# Expected: Routes to Assessment Agent, recognizes anxiety symptoms

# To run tests, uncomment below and use in run_agent.py or create test_runner.py
"""
from llm_clients import GroqClient, GeminiClient
from specialized_agents import CoordinatorAgent
import os
from dotenv import load_dotenv

load_dotenv()
llm = GroqClient()  # or GeminiClient()
coordinator = CoordinatorAgent(llm)

test_cases = [
    ("Crisis", test_crisis),
    ("Assessment", test_assessment),
    ("Therapy", test_therapy),
    ("Resource", test_resource),
    ("General", test_general),
    ("Follow-up", test_followup)
]

for name, test_input in test_cases:
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"Input: {test_input}")
    result = coordinator.process(test_input)
    print(f"Routed to: {result['routed_to']}")
    print(f"Response: {result['text']}")
"""
