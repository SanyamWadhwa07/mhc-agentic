import os
import json
from dotenv import load_dotenv

from llm_clients import GroqClient, GeminiClient

# New Architecture Imports
from safety import ImmediateCrisisDetector, ContentModeration, InputSanitizer, OutputSafetyScrubber
from tools import *
from core import Controller, ToolExecutionEngine

# Agent-Lightning Instrumentation
from instrumentation import create_traced_client, TraceStore

def select_llm():
    provider = os.getenv('LLM_PROVIDER', 'groq').lower()
    if provider == 'groq':
        return GroqClient()
    if provider == 'gemini':
        return GeminiClient()
    raise ValueError('Unsupported LLM_PROVIDER: ' + provider)


def select_master_llm():
    """Select larger model for master agent synthesis."""
    provider = os.getenv('LLM_PROVIDER', 'groq').lower()
    if provider == 'groq':
        # Use larger model for master agent
        model = os.getenv('GROQ_MASTER_MODEL', 'llama-3.3-70b-versatile')
        return GroqClient(model=model)
    if provider == 'gemini':
        model = os.getenv('GEMINI_MASTER_MODEL', 'gemini-1.5-pro')
        return GeminiClient(model=model)
    raise ValueError('Unsupported LLM_PROVIDER: ' + provider)


def main():
    load_dotenv()
    
    # Debug mode toggle
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    # Initialize trace store (if tracing enabled)
    trace_store = TraceStore(trace_dir="traces")
    
    # Initialize LLMs with optional tracing
    base_controller_llm = select_llm()  # Fast model for controller
    base_master_llm = select_master_llm()  # Strong model for responder
    
    # Wrap with tracing (controlled by ENABLE_TRACING env var)
    controller_llm = create_traced_client(base_controller_llm, "Controller", trace_store)
    master_llm = create_traced_client(base_master_llm, "MasterResponder", trace_store)
    
    # Initialize Safety Components (Stage 1)
    crisis_detector = ImmediateCrisisDetector()
    content_moderator = ContentModeration()
    input_sanitizer = InputSanitizer()
    output_scrubber = OutputSafetyScrubber()
    
    # Initialize Tools
    tool_registry = {
        "EmotionTool": EmotionTool(),
        "SentimentTool": SentimentTool(),
        "MemoryReadTool": MemoryReadTool(controller_llm),
        "MemoryWriteTool": MemoryWriteTool(controller_llm),
        "PatternDetectorTool": PatternDetectorTool(),
        "InterventionSelectorTool": InterventionSelectorTool(),
        "AssessmentTool": AssessmentTool(),
        "TherapyTool": TherapyTool(controller_llm),
        "ResourceTool": ResourceTool(controller_llm),
        "MasterResponderTool": MasterResponderTool(master_llm)
    }
    
    # Initialize Core Components (Stage 2)
    controller = Controller(controller_llm, tool_registry)
    engine = ToolExecutionEngine(tool_registry)

    if debug_mode:
        print('\n' + '=' * 80)
        print('🔍 DEBUG MODE ENABLED - Showing All Internal Processing 🔍')
        print('=' * 80)
    
    print('\n' + '=' * 60)
    print('💙  Hey there! I\'m here to listen and support you  💙')
    print('=' * 60)
    print()
    print('I\'m like a friend who\'s here whenever you need to talk.')
    print('Share what\'s on your mind - there\'s no judgment here.')
    print()
    print('Whether you\'re:')
    print('  • Going through a tough time')
    print('  • Feeling stressed, anxious, or down')
    print('  • Looking for coping strategies')
    print('  • Just need someone to listen')
    print()
    print('...I\'m here for you. Let\'s talk.')
    print()
    if debug_mode:
        print('(Debug mode active - you\'ll see all internal processing)')
    print('(Type "exit" anytime to end our conversation)')
    print('=' * 60)
    print()
    
    while True:
        user_input = input('\n💬 You: ').strip()
        if not user_input:
            continue
        if user_input.lower() in ('exit', 'quit'):
            print('\n💙 Thank you for sharing with me today.')
            print('Remember: I\'m always here when you need to talk.')
            print('\nIf you ever need immediate help:')
            print('  • Call or text 988 (Suicide & Crisis Lifeline)')
            print('  • Text HOME to 741741 (Crisis Text Line)')
            print('\nTake care of yourself. You matter. 💙\n')
            break
        
        # --- STAGE 1: FIXED SAFETY PIPELINE ---
        
        # 1. Crisis Detection
        crisis_result = crisis_detector.check(user_input)
        if crisis_result['risk_level'] == 'high':
            print(f"\n⚠️ IMMEDIATE CRISIS DETECTED ({crisis_result.get('crisis_type')})")
            print("Please contact emergency services immediately.")
            print("Suicide & Crisis Lifeline: 988")
            continue
            
        # 2. Content Moderation
        mod_result = content_moderator.check(user_input)
        if mod_result['blocked']:
            print("\n⚠️ I cannot process this message due to safety guidelines.")
            continue
            
        # 3. Input Sanitization
        sanitized = input_sanitizer.sanitize(user_input)
        safe_input = sanitized['safe_input']
        
        if debug_mode:
            print(f"\n[Safety] Risk: {crisis_result['risk_level']}, Safe Input: {safe_input}")
            
        # --- STAGE 2: AGENTIC ORCHESTRATION ---
        
        # 1. Controller Decision
        # For now, we pass a dummy session summary. In real app, fetch from memory.
        session_summary = "Session in progress." 
        
        plan = controller.decide(safe_input, crisis_result['risk_level'], session_summary)
        
        if debug_mode:
            print("\n[Controller Plan]")
            print(json.dumps(plan, indent=2))
            
        # 2. Tool Execution
        context = {
            "risk_level": crisis_result['risk_level'],
            "session_summary": session_summary
        }
        execution_result = engine.execute_plan(plan, safe_input, context)
        
        if debug_mode:
            print("\n[Tool Results]")
            print(json.dumps(execution_result['tool_results'], indent=2, default=str))
            
        # 3. Final Response
        final_response = execution_result.get('final_response', {})
        reply_text = final_response.get('reply_text', "I'm sorry, I couldn't generate a response.")
        
        # 4. Output Safety Scrubbing
        scrubbed = output_scrubber.scrub(reply_text)
        if not scrubbed['approved']:
            print(f"\n⚠️ Output blocked by safety scrubber: {scrubbed.get('violation')}")
            if debug_mode:
                print(f"Original: {scrubbed.get('original_response')}")
            reply_text = scrubbed['safe_response']
        
        print(f'\n💙 {reply_text}\n')


if __name__ == '__main__':
    main()
