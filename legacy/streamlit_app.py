"""
Streamlit web interface for Mental Health Chatbot.
Deploy with: streamlit run streamlit_app.py
"""

import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from collaborative_agents import MasterAgent
from conversation_memory import ConversationMemory
from assessment_tracker import AssessmentTracker
from mood_tracker import MoodTracker
from nlp_enhancements import SentimentAnalyzer
from llm_clients import GroqClient, GeminiClient

# Page config
st.set_page_config(
    page_title="Mental Health Support Chat",
    page_icon="💙",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .main {
        background-color: #f5f7fa;
    }
    .block-container {
        padding-top: 2rem;
        max-width: 800px;
    }
    h1 {
        color: #2c3e50;
        font-weight: 600;
    }
    .stButton button {
        background-color: #3498db;
        color: white;
        border-radius: 0.5rem;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .stButton button:hover {
        background-color: #2980b9;
    }
    .crisis-banner {
        background-color: #e74c3c;
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .mood-info {
        background-color: #ecf0f1;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.messages = []
    st.session_state.system_initialized = False
    st.session_state.conversation_count = 0
    st.session_state.show_crisis_warning = False
    st.session_state.debug_mode = False
    st.session_state.agent_system = None  # Initialize agent_system key

# Initialize chatbot components
def initialize_chatbot(session_id):
    """Initialize all chatbot components with specific session ID."""
    try:
        # Initialize LLM clients
        expert_llm = GroqClient(model="llama-3.1-8b-instant")
        master_llm = GroqClient(model="llama-3.3-70b-versatile")
        agent_system = MasterAgent(llm_client=expert_llm, master_llm_client=master_llm)
        # Override the agent's session ID to match our web session
        agent_system.session_id = session_id
        agent_system.memory.session_id = session_id
        agent_system.assessment_tracker.session_id = session_id
        agent_system.mood_tracker.session_id = session_id
        return agent_system
    except ValueError as e:
        st.error(f"""
        ### ⚠️ API Key Required
        
        {str(e)}
        
        **Setup Instructions:**
        1. Create a `.env` file in the project root
        2. Add your API keys:
           ```
           GROQ_API_KEY=your_groq_api_key_here
           GEMINI_API_KEY=your_gemini_api_key_here
           ```
        3. Get free API keys:
           - Groq: https://console.groq.com
           - Gemini: https://ai.google.dev
        
        For Streamlit Cloud deployment, add these as secrets in the dashboard.
        """)
        st.stop()
        return None

def get_session_components(session_id):
    """Get or create session-specific components."""
    memory = ConversationMemory(session_id)
    assessment = AssessmentTracker(session_id)
    mood_tracker = MoodTracker(session_id)
    nlp_analyzer = SentimentAnalyzer()
    return memory, assessment, mood_tracker, nlp_analyzer

# Initialize agent system only once per session
if st.session_state.get('agent_system') is None:
    st.session_state.agent_system = initialize_chatbot(st.session_state.session_id)

agent_system = st.session_state.agent_system
memory, assessment, mood_tracker, nlp_analyzer = get_session_components(st.session_state.session_id)

# Sidebar for settings
with st.sidebar:
    st.title("⚙️ Settings")
    st.session_state.debug_mode = st.checkbox("🔍 Debug Mode", value=st.session_state.debug_mode)
    
    if st.button("🔄 New Session"):
        st.session_state.session_id = f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.messages = []
        st.session_state.conversation_count = 0
        st.session_state.show_crisis_warning = False
        st.session_state.agent_system = initialize_chatbot(st.session_state.session_id)
        memory, assessment, mood_tracker, nlp_analyzer = get_session_components(st.session_state.session_id)
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Session Stats")
    st.metric("Messages", st.session_state.conversation_count)
    st.metric("Session ID", st.session_state.session_id[-8:])  # Last 8 chars
    
    if st.session_state.conversation_count >= 3:
        trend = mood_tracker.get_mood_trend()
        trend_emoji = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️",
            "establishing_baseline": "📊"
        }.get(trend, "📊")
        st.metric("Mood Trend", f"{trend_emoji} {trend.replace('_', ' ').title()}")
        
        # Show mood pattern in debug mode
        if st.session_state.debug_mode:
            pattern = mood_tracker.get_emotional_pattern()
            st.markdown("**Emotional Pattern:**")
            for emotion, count in list(pattern.items())[:3]:
                st.text(f"  {emotion}: {count}x")
    
    # Show assessment summary in debug mode
    if st.session_state.debug_mode and st.session_state.conversation_count >= 5:
        st.markdown("---")
        st.markdown("### 📋 Assessment Snapshot")
        scores = assessment.calculate_scores()
        
        if assessment.responses:
            symptoms = list(assessment.responses.keys())[:2]
            for symptom in symptoms:
                st.text(f"• {symptom}")
        
        st.markdown(f"**Estimated Screening:**")
        st.text(f"PHQ-9: ~{scores.get('phq9_estimated', 0)}/27")
        st.text(f"GAD-7: ~{scores.get('gad7_estimated', 0)}/21")
    
    st.markdown("---")
    st.markdown("""
    ### 🆘 Crisis Resources
    **988 Suicide & Crisis Lifeline**  
    Call/Text: 988  
    Available 24/7
    
    **Crisis Text Line**  
    Text HOME to 741741  
    Available 24/7
    """)

# Main interface
st.title("💙 Mental Health Support Chat")

# Crisis warning banner
if st.session_state.show_crisis_warning:
    st.markdown("""
    <div class="crisis-banner">
        ⚠️ If you're in crisis, please reach out to 988 Suicide & Crisis Lifeline immediately. 
        Call or text 988 for 24/7 support.
    </div>
    """, unsafe_allow_html=True)

# Welcome message
if not st.session_state.messages:
    welcome_msg = "Hey, I'm here to listen. What's on your mind?"
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process message
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Analyze sentiment and update mood
                sentiment = nlp_analyzer.analyze(prompt)
                mood_tracker.record_mood(sentiment, prompt)
                
                # Check for crisis
                if sentiment.get('crisis_detected'):
                    st.session_state.show_crisis_warning = True
                
                # Update assessment tracker
                assessment.analyze_message(prompt)
                
                # Generate response using MasterAgent
                # Note: MasterAgent uses its own session management
                try:
                    response_data = agent_system.process(user_input=prompt)
                    # Agent returns 'text' key, not 'response'
                    response = response_data.get('text') or response_data.get('response', "I'm here for you. Can you tell me more?")
                    
                    # Debug: Show if response is the fallback
                    if st.session_state.debug_mode and response == "I'm here for you. Can you tell me more?":
                        st.warning("⚠️ Using fallback response - check response_data")
                        st.json(response_data)
                        
                except Exception as agent_error:
                    st.error(f"❌ Agent Error: {str(agent_error)}")
                    if st.session_state.debug_mode:
                        st.exception(agent_error)
                    response = "I'm having trouble processing that. Can you try rephrasing?"
                    response_data = {}
                
                # Display response
                st.markdown(response)
                
                # Comprehensive Debug Panel
                if st.session_state.debug_mode:
                    st.markdown("---")
                    st.markdown("### 🔍 Comprehensive Debug Panel")
                    
                    # Create tabs for organized debug info
                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "🎭 Emotions", "📊 Mood", "🤖 Agents", "🧠 NLP", "📋 Assessment"
                    ])
                    
                    with tab1:
                        st.markdown("#### Emotion Detection")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Primary Emotion", sentiment.get('emotion', 'neutral').upper())
                            st.metric("Sentiment Score", f"{sentiment.get('sentiment_score', 0):.2f}")
                            st.metric("Urgency Level", sentiment.get('urgency', 'normal').upper())
                        with col2:
                            all_emotions = sentiment.get('emotions', [])
                            if all_emotions:
                                st.markdown("**All Detected Emotions:**")
                                for emotion in all_emotions:
                                    st.markdown(f"- `{emotion}`")
                            else:
                                st.info("No specific emotions detected")
                        
                        st.markdown("**Emotion Indicators:**")
                        st.text(f"Positive words: {sentiment.get('positive_indicators', 0)}")
                        st.text(f"Negative words: {sentiment.get('negative_indicators', 0)}")
                        
                        if sentiment.get('crisis_detected'):
                            st.error("⚠️ CRISIS DETECTED - Safety resources triggered")
                    
                    with tab2:
                        st.markdown("#### Mood Tracking")
                        
                        # Current mood point
                        st.markdown("**Current Mood Point:**")
                        st.json({
                            "emotion": sentiment.get('emotion'),
                            "sentiment_score": sentiment.get('sentiment_score'),
                            "urgency": sentiment.get('urgency')
                        })
                        
                        # Mood trend
                        if len(list(mood_tracker.mood_history)) >= 3:
                            trend = mood_tracker.get_mood_trend()
                            pattern = mood_tracker.get_emotional_pattern()
                            guidance = mood_tracker.get_response_guidance()
                            
                            st.markdown("**Mood Trend Analysis:**")
                            st.text(f"Trend: {trend}")
                            
                            st.markdown("**Emotional Pattern (Recent):**")
                            for emotion, count in list(pattern.items())[:5]:
                                st.progress(min(count / 5, 1.0), text=f"{emotion}: {count}x")
                            
                            st.markdown("**Response Guidance:**")
                            st.json(guidance)
                        else:
                            st.info("Need 3+ messages for trend analysis")
                        
                        # Mood history chart
                        if len(list(mood_tracker.mood_history)) >= 2:
                            st.markdown("**Sentiment History:**")
                            history_data = {
                                "Message": list(range(1, len(mood_tracker.mood_history) + 1)),
                                "Score": [m['sentiment_score'] for m in mood_tracker.mood_history]
                            }
                            st.line_chart(history_data, x="Message", y="Score")
                    
                    with tab3:
                        st.markdown("#### Multi-Agent System")
                        
                        # Show which agents contributed
                        if 'expert_contributions' in response_data:
                            st.markdown("**Active Expert Agents:**")
                            contributions = response_data['expert_contributions']
                            
                            for expert_name, contribution in contributions.items():
                                with st.expander(f"🤖 {expert_name}", expanded=False):
                                    st.markdown(f"**Contribution:**")
                                    st.info(contribution.get('response', 'N/A'))
                                    
                                    if 'relevant_docs' in contribution:
                                        st.markdown("**Retrieved Documents:**")
                                        for i, doc in enumerate(contribution['relevant_docs'][:2], 1):
                                            st.text(f"{i}. {doc.get('title', 'Untitled')[:50]}...")
                                            st.caption(f"Relevance: {doc.get('score', 0):.2%}")
                        else:
                            st.info("Agent contributions not available in response")
                        
                        # Show master synthesis
                        st.markdown("**Master Agent Synthesis:**")
                        st.text(f"Response length: {len(response)} chars")
                        st.text(f"Token estimate: ~{len(response.split())} words")
                        
                    with tab4:
                        st.markdown("#### NLP Analysis")
                        
                        # Full sentiment breakdown
                        st.markdown("**Complete Sentiment Analysis:**")
                        st.json(sentiment)
                        
                        # Conversation insights (if available)
                        st.markdown("**Conversation Context:**")
                        st.text(f"Total messages: {len(st.session_state.messages)}")
                        st.text(f"User message length: {len(prompt.split())} words")
                        st.text(f"Average response length: ~{sum(len(m['content'].split()) for m in st.session_state.messages if m['role']=='assistant') // max(1, sum(1 for m in st.session_state.messages if m['role']=='assistant'))} words")
                        
                        # Show message history from agent's memory
                        agent_history = agent_system.memory.get_recent_messages()
                        if len(agent_history) > 0:
                            with st.expander("📜 Conversation History (in agent memory)", expanded=False):
                                for i, msg in enumerate(agent_history, 1):
                                    role_emoji = "👤" if msg['role'] == "User" else "🤖"
                                    st.markdown(f"{role_emoji} **{msg['role']}**: {msg['content'][:100]}...")
                    
                    with tab5:
                        st.markdown("#### Clinical Assessment (Non-Diagnostic)")
                        
                        # Calculate scores
                        scores = assessment.calculate_scores()
                        phq9_score = scores.get('phq9_estimated', 0)
                        gad7_score = scores.get('gad7_estimated', 0)
                        
                        # Screening scores
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("PHQ-9 Estimate", f"~{phq9_score}/27")
                            phq_level = "Minimal" if phq9_score < 5 else "Mild" if phq9_score < 10 else "Moderate" if phq9_score < 15 else "Moderately Severe" if phq9_score < 20 else "Severe"
                            st.caption(f"Range: {phq_level}")
                        with col2:
                            st.metric("GAD-7 Estimate", f"~{gad7_score}/21")
                            gad_level = "Minimal" if gad7_score < 5 else "Mild" if gad7_score < 10 else "Moderate" if gad7_score < 15 else "Severe"
                            st.caption(f"Range: {gad_level}")
                        
                        # Show detected symptoms
                        if assessment.responses:
                            st.markdown("**Discussed Symptoms:**")
                            for symptom in assessment.responses.keys():
                                mentions = len(assessment.responses[symptom])
                                st.markdown(f"- {symptom}: {mentions}x mentioned")
                        
                        # Risk level and concerns
                        if scores.get('concerns'):
                            st.markdown("**Assessment Notes:**")
                            for concern in scores['concerns']:
                                st.info(concern)
                        
                        st.metric("Risk Level", scores.get('risk_level', 'unknown').upper())
                        
                        st.caption("⚠️ These are estimates based on conversation - NOT a clinical diagnosis")
                
                # Add assistant response to chat
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.conversation_count += 1
                
                # Save to memory
                memory.add_message("User", prompt)
                memory.add_message("Assistant", response)
                
            except Exception as e:
                error_msg = "I'm having trouble right now. Can you try again?"
                st.error(error_msg)
                if st.session_state.debug_mode:
                    st.exception(e)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; font-size: 0.85rem;'>
    This is a support tool, not a replacement for professional mental health care.<br>
    If you're in crisis, please contact 988 or visit your nearest emergency room.
</div>
""", unsafe_allow_html=True)
