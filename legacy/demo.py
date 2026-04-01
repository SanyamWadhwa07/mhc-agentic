"""
Demo script to show the chatbot in action.
Runs a few test conversations to demonstrate the system.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Check if API key is set
if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    print("❌ ERROR: No API key found!")
    print("\nPlease set an API key in .env file:")
    print("  For Groq: GROQ_API_KEY=your_key_here")
    print("  For Gemini: GEMINI_API_KEY=your_key_here")
    sys.exit(1)

print("="*70)
print("Mental Health Chatbot - System Demo")
print("="*70)
print("\nThis demo shows the hybrid agentic architecture in action.")
print("Watch how the system processes messages through:")
print("  1. Safety Pipeline (Stage 1)")
print("  2. Agentic Orchestration (Stage 2)")
print("  3. Output Safety (Stage 3)\n")

# Import components
from llm_clients import GroqClient, GeminiClient
from safety import ImmediateCrisisDetector, ContentModeration, InputSanitizer, OutputSafetyScrubber
from tools import *
from core import Controller, ToolExecutionEngine
from instrumentation import create_traced_client, TraceStore

def select_llm():
    provider = os.getenv('LLM_PROVIDER', 'groq').lower()
    if provider == 'groq':
        return GroqClient()
    if provider == 'gemini':
        return GeminiClient()
    raise ValueError('Unsupported LLM_PROVIDER')

def select_master_llm():
    provider = os.getenv('LLM_PROVIDER', 'groq').lower()
    if provider == 'groq':
        model = os.getenv('GROQ_MASTER_MODEL', 'llama-3.3-70b-versatile')
        return GroqClient(model=model)
    if provider == 'gemini':
        model = os.getenv('GEMINI_MASTER_MODEL', 'gemini-1.5-pro')
        return GeminiClient(model=model)

def process_message(user_message, components):
    """Process a single message through the pipeline."""
    print(f"\n{'='*70}")
    print(f"💬 User: {user_message}")
    print(f"{'='*70}\n")
    
    # Stage 1: Safety Pipeline
    print("🔒 STAGE 1: Safety Pipeline")
    print("-" * 70)
    
    # Sanitize
    sanitized = components['sanitizer'].execute(user_message)
    clean_text = sanitized['sanitized_text']
    print(f"  ✓ Input Sanitizer: Cleaned text")
    
    # Crisis detection
    crisis_result = components['crisis_detector'].execute(clean_text)
    risk_level = crisis_result['risk_level']
    print(f"  ✓ Crisis Detector: Risk level = {risk_level}")
    
    if risk_level == "High":
        print("\n  ⚠️  HIGH RISK DETECTED - Returning crisis resources")
        return "I'm concerned about your safety. Please reach out for immediate help:\n• Call 988 (Suicide & Crisis Lifeline)\n• Text HOME to 741741 (Crisis Text Line)"
    
    # Content moderation
    mod_result = components['content_moderator'].execute(clean_text)
    if mod_result['is_blocked']:
        print("  ✗ Content Moderator: Blocked")
        return "I'm not able to respond to that. Let's refocus on supportive conversation."
    print("  ✓ Content Moderator: Appropriate\n")
    
    # Stage 2: Agentic Orchestration
    print("🤖 STAGE 2: Agentic Orchestration")
    print("-" * 70)
    
    try:
        # Controller decides tools
        print("  → Controller: Deciding tool sequence...")
        plan = components['controller'].decide(clean_text, risk_level, "")
        tools_to_call = [item.get('name') for item in plan.get('tool_sequence', [])]
        print(f"  ✓ Selected tools: {', '.join(tools_to_call) if tools_to_call else 'None'}")
        
        # Execute tools
        print(f"  → Executing {len(tools_to_call)} tools...")
        context = components['engine'].execute_plan(plan, clean_text, risk_level, "")
        print(f"  ✓ Tool execution complete\n")
        
        # Master Responder
        print("  → Master Responder: Generating empathetic response...")
        prompt = f"""User said: {clean_text}

Context from tools:
{str(context)[:200]}...

Generate a warm, empathetic, therapeutic response (1-2 sentences max)."""
        
        master_result = components['master_responder'].execute({"prompt_context": prompt})
        response = master_result.get('reply_text', "I'm here to listen. Tell me more about what you're experiencing.")
        print(f"  ✓ Response generated\n")
        
    except Exception as e:
        print(f"  ⚠️  Error in orchestration: {str(e)}")
        response = "I'm here to support you. Could you tell me more about how you're feeling?"
    
    # Stage 3: Output Safety
    print("🛡️  STAGE 3: Output Safety")
    print("-" * 70)
    scrub_result = components['output_scrubber'].execute(response)
    if not scrub_result['is_safe']:
        print(f"  ✗ Output blocked: {scrub_result['reason']}")
        response = "I apologize, but I need to rephrase that response. How else can I support you today?"
    else:
        print("  ✓ Output approved\n")
    
    print("="*70)
    print(f"🤖 Bot: {response}")
    print("="*70)
    
    return response

def main():
    # Initialize components
    print("\n📦 Initializing system components...")
    
    trace_store = TraceStore(trace_dir="traces")
    base_controller_llm = select_llm()
    base_master_llm = select_master_llm()
    
    # Enable tracing if configured
    controller_llm = create_traced_client(base_controller_llm, "Controller", trace_store)
    master_llm = create_traced_client(base_master_llm, "MasterResponder", trace_store)
    
    # Safety components
    crisis_detector = ImmediateCrisisDetector()
    content_moderator = ContentModeration()
    input_sanitizer = InputSanitizer()
    output_scrubber = OutputSafetyScrubber()
    
    # Tools
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
    
    # Core
    controller = Controller(controller_llm, tool_registry)
    engine = ToolExecutionEngine(tool_registry)
    
    components = {
        'sanitizer': input_sanitizer,
        'crisis_detector': crisis_detector,
        'content_moderator': content_moderator,
        'controller': controller,
        'engine': engine,
        'master_responder': MasterResponderTool(master_llm),
        'output_scrubber': output_scrubber
    }
    
    print("✅ System ready!\n")
    
    # Test conversations
    test_messages = [
        "I'm feeling stressed about work",
        "I've been having trouble sleeping lately",
        "Thank you for listening"
    ]
    
    for msg in test_messages:
        try:
            process_message(msg, components)
            print("\n" + "·"*70 + "\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
    
    print("\n" + "="*70)
    print("✅ Demo complete!")
    print("="*70)
    print("\nNext steps:")
    print("  • Enable tracing: Set ENABLE_TRACING=true in .env")
    print("  • Run optimization: python scripts/train_agent.py --mode=all")
    print("  • View traces: python scripts/train_agent.py --mode=analyze")

if __name__ == "__main__":
    main()
