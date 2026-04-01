"""
Multi-agent collaboration system where specialized agents help a master agent
formulate the best response by contributing their expertise.
"""
from typing import Dict, Any, List
from knowledge_base import RAGAgent
from conversation_memory import ConversationMemory
from assessment_tracker import AssessmentTracker
from nlp_enhancements import ConversationalContext
from mood_tracker import MoodTracker


class CollaborativeAgent(RAGAgent):
    """Agent that can contribute expertise to collaborative decision-making."""
    
    def __init__(self, llm_client, agent_type: str, system_prompt: str):
        super().__init__(llm_client, agent_type, system_prompt)
    
    def contribute(self, user_input: str, task_description: str) -> Dict[str, Any]:
        """Contribute specialized knowledge to help formulate a response."""
        # Retrieve relevant context
        context_docs = self.knowledge_base.search(user_input, top_k=3)
        
        # Build prompt for contribution
        prompt = f"""{self.system_prompt}

=== TASK ===
{task_description}

=== RELEVANT KNOWLEDGE FROM YOUR DOMAIN ===
"""
        if context_docs:
            for i, doc in enumerate(context_docs, 1):
                prompt += f"\n[Knowledge {i}] {doc['title']}\n{doc['content']}\n"
        
        prompt += f"""
=== USER MESSAGE ===
{user_input}

=== YOUR CONTRIBUTION ===
Provide ONE brief insight (1 sentence max) from your expertise.
No explanations, no lists, no advice - just the key point.
"""
        
        # Generate contribution - brief, focused insight only
        resp = self.llm.generate(prompt, max_tokens=60, temperature=0.8)
        text = self._extract_text(resp)
        
        # Clean up verbose responses - keep only first 1-2 sentences
        sentences = text.split('. ')
        if len(sentences) > 2:
            text = '. '.join(sentences[:2]) + '.'
        
        return {
            "agent_type": self.agent_type,
            "contribution": text,
            "context_used": [doc['title'] for doc in context_docs],
            "relevance_scores": [doc.get('relevance_score', 0) for doc in context_docs]
        }


class AssessmentCollaborator(CollaborativeAgent):
    """Assessment expert that contributes clinical screening insights."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a clinical assessment expert specializing in mental health screening and evaluation.
Your expertise includes: symptom identification, assessment tools (PHQ-9, GAD-7), severity evaluation,
red flags for urgent care, and differential diagnosis considerations."""
        super().__init__(llm_client, 'assessment', system_prompt)


class TherapyCollaborator(CollaborativeAgent):
    """Therapy expert that contributes evidence-based intervention insights."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a supportive friend with expertise in coping strategies and mental wellness.
Your role is to suggest helpful coping strategies in a friendly, accessible way.
Share practical techniques people can try right away. Validate feelings and normalize struggles.
Use the knowledge provided but translate it into warm, everyday language."""
        super().__init__(llm_client, 'therapy', system_prompt)


class CrisisCollaborator(CollaborativeAgent):
    """Crisis expert that contributes safety and emergency response insights."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a crisis intervention expert specializing in safety assessment and emergency response.
Your expertise includes: suicide risk assessment, crisis hotlines, safety planning, means restriction,
de-escalation techniques, and emergency resources."""
        super().__init__(llm_client, 'crisis', system_prompt)


class ResourceCollaborator(CollaborativeAgent):
    """Resource expert that contributes professional referral and system navigation insights."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a mental health resource expert specializing in connecting people to professional help.
Your expertise includes: types of mental health professionals, therapy modalities, insurance navigation,
support groups, community resources, and treatment options."""
        super().__init__(llm_client, 'resource', system_prompt)


class MasterAgent:
    """
    Master agent that coordinates specialized agents to formulate optimal responses.
    Collects input from all relevant specialized agents and synthesizes the best response.
    Uses larger LLM for better synthesis while expert agents use smaller models.
    """
    
    def __init__(self, llm_client, master_llm_client=None):
        # Expert agents use smaller, faster models with RAG
        self.llm = llm_client
        # Master agent uses larger model for better synthesis (optional)
        self.master_llm = master_llm_client or llm_client
        
        self.assessment_agent = AssessmentCollaborator(llm_client)
        self.therapy_agent = TherapyCollaborator(llm_client)
        self.crisis_agent = CrisisCollaborator(llm_client)
        self.resource_agent = ResourceCollaborator(llm_client)
        
        # Conversation memory with auto-summarization
        self.memory = ConversationMemory(llm_client)
        
        # Background assessment tracker
        self.assessment_tracker = AssessmentTracker(self.memory.session_id)
        
        # NLP enhancements for analytical backend
        self.nlp_context = ConversationalContext()
        
        # Mood tracker for emotion-aware responses
        self.mood_tracker = MoodTracker(self.memory.session_id)
        
        # Session ID for continuity
        self.session_id = self.memory.session_id
        
        self.conversation_history = []
        
        self.master_prompt = """You are a real friend having an emotional conversation.

Your communication style:
- ULTRA SHORT: 1-3 sentences. Humans in emotional conversations don't write paragraphs.
- NO CLINICAL LANGUAGE: Never say "emotional state", "vulnerability", "therapeutic", "process"
- NO TEMPLATES: Banned phrases: "It sounds like", "I can hear", "When someone", "It's normal"
- USE MICRO-EMPATHY: "ouch", "damn", "that's rough", "I'd feel the same", "oof"
- MIRROR INTENSITY: If they're angry/hurt, you get shorter and more direct
- Sometimes just PAUSE: Don't always ask questions. Sometimes just be there.

Response patterns:
1. Short emotional acknowledgment: "Yeah... that's the part that breaks the hardest."
2. One grounding line: "When trust goes, the whole relationship feels different."
3. Simple question OR just presence: "What changed for you?" OR just stop there.

Intensity mirroring:
- High emotion (betrayal, hate, pain) → 1-2 sentences, no questions, just presence
- Medium emotion (sadness, hurt) → 2 sentences + small question
- Low emotion (thinking, reflecting) → Can explore more

Examples of GOOD responses:
"Ouch. That would hit me hard too."
"Damn... I'd be hurt too. What part stings most?"
"Yeah. Trust breaks everything."
"That's rough. You don't have to explain more right now."

Examples of BAD responses:
"I can hear how this emotional experience is affecting your vulnerable state..."
"It sounds like you're processing complex feelings about trust..."
"When someone betrays us, it's normal to feel..."

You are NOT a therapist. You are a friend who gets it."""
    
    def _detect_relevant_agents(self, user_input: str) -> List[str]:
        """Determine which specialized agents should contribute (legacy - prefer _smart_expert_selection)."""
        lower_input = user_input.lower()
        relevant_agents = []
        
        # Crisis - always check first
        crisis_keywords = ['suicide', 'kill myself', 'end my life', 'harm myself', 
                          'want to die', 'self-harm', 'cutting', 'overdose', 'can\'t go on']
        if any(keyword in lower_input for keyword in crisis_keywords):
            relevant_agents.append('crisis')
            relevant_agents.append('assessment')  # Also need assessment for crisis
            return relevant_agents  # Crisis takes priority
        
        # Assessment indicators
        assessment_keywords = ['feeling', 'symptoms', 'depressed', 'anxious', 'stressed',
                               'not sleeping', 'sleep', 'appetite', 'worried', 'sad', 'scared',
                               'panic', 'how bad', 'severe', 'diagnosis']
        if any(keyword in lower_input for keyword in assessment_keywords):
            relevant_agents.append('assessment')
        
        # Therapy/coping indicators
        therapy_keywords = ['help me', 'what can i do', 'cope', 'coping', 'manage', 'feel better',
                           'technique', 'strategy', 'exercise', 'relax', 'calm', 'meditation',
                           'breathing', 'mindfulness', 'deal with']
        if any(keyword in lower_input for keyword in therapy_keywords):
            relevant_agents.append('therapy')
        
        # Resource indicators
        resource_keywords = ['therapist', 'counselor', 'psychiatrist', 'find help', 'professional',
                            'support group', 'treatment', 'medication', 'doctor', 'insurance',
                            'how do i find', 'where can i', 'who should i see']
        if any(keyword in lower_input for keyword in resource_keywords):
            relevant_agents.append('resource')
        
        # If unclear or general, include therapy (most versatile)
        if not relevant_agents:
            relevant_agents.append('therapy')
            relevant_agents.append('assessment')  # Also helpful for general mental health
        
        return relevant_agents
    
    def _smart_expert_selection(self, sentiment: Dict, topics: List[str], user_input: str) -> List[str]:
        """Smart expert selection using NLP insights."""
        relevant_agents = []
        
        # Crisis detection using sentiment analysis
        if sentiment.get('crisis_detected') or sentiment.get('urgency') == 'high':
            relevant_agents.append('crisis')
            relevant_agents.append('assessment')
            return relevant_agents  # Crisis takes priority
        
        # Topic-based selection
        topic_to_agent = {
            'depression': 'assessment',
            'anxiety': 'assessment',
            'stress': 'assessment',
            'coping': 'therapy',
            'therapy': 'therapy',
            'mindfulness': 'therapy',
            'professional help': 'resource',
            'medication': 'resource',
            'support': 'resource',
            'sleep': 'assessment',
            'panic': 'assessment'
        }
        
        for topic in topics:
            if topic in topic_to_agent:
                agent = topic_to_agent[topic]
                if agent not in relevant_agents:
                    relevant_agents.append(agent)
        
        # Emotion-based selection
        emotion = sentiment.get('emotion', 'neutral')
        if emotion in ['crisis', 'distressed']:
            if 'crisis' not in relevant_agents:
                relevant_agents.append('crisis')
            if 'assessment' not in relevant_agents:
                relevant_agents.append('assessment')
        elif emotion in ['struggling', 'coping']:
            if 'therapy' not in relevant_agents:
                relevant_agents.append('therapy')
            if 'assessment' not in relevant_agents:
                relevant_agents.append('assessment')
        
        # Fallback to keyword-based if no topics matched
        if not relevant_agents:
            relevant_agents = self._detect_relevant_agents(user_input)
        
        return relevant_agents
        
        return relevant_agents
    
    def process(self, user_input: str) -> Dict[str, Any]:
        """Process user input with collaborative multi-agent approach."""
        
        # Get conversation history for NLP analysis
        conversation_history = [
            {'role': msg['role'], 'content': msg['content']} 
            for msg in self.memory.get_recent_messages()
        ]
        
        # NLP analysis for analytical backend
        nlp_analysis = self.nlp_context.analyze_message(
            self.session_id, 
            user_input, 
            conversation_history
        )
        
        # Extract NLP insights
        sentiment = nlp_analysis['sentiment']
        topics = nlp_analysis['topics']
        patterns = nlp_analysis['patterns']
        personalization = nlp_analysis['personalization']
        learned_recommendations = nlp_analysis['learned_recommendations']
        
        # Record mood for tracking
        self.mood_tracker.record_mood(sentiment, user_input)
        mood_guidance = self.mood_tracker.get_response_guidance()
        
        # First message - give a warm greeting
        if len(self.memory.messages) == 0:
            greeting_added = True
        else:
            greeting_added = False
        
        # Background assessment analysis (invisible to user)
        assessment_analysis = self.assessment_tracker.analyze_message(user_input)
        
        # Add user message to memory with NLP metadata
        self.memory.add_message('User', user_input, metadata={
            **assessment_analysis,
            'sentiment': sentiment,
            'topics': topics,
            'emotion': sentiment.get('emotion'),
            'urgency': sentiment.get('urgency')
        })
        
        # Smart expert selection using NLP insights
        relevant_agent_types = self._smart_expert_selection(sentiment, topics, user_input)
        
        # Collect contributions from relevant specialized agents with enhanced context
        contributions = []
        enhanced_context = nlp_analysis['enhanced_context']
        task_description = f"Help formulate the best response to a user seeking mental health support. {enhanced_context}"
        
        agent_map = {
            'assessment': self.assessment_agent,
            'therapy': self.therapy_agent,
            'crisis': self.crisis_agent,
            'resource': self.resource_agent
        }
        
        for agent_type in relevant_agent_types:
            agent = agent_map[agent_type]
            contribution = agent.contribute(user_input, task_description)
            contributions.append(contribution)
        
        # Master agent synthesizes all contributions with NLP insights and mood guidance
        synthesis_prompt = self._build_synthesis_prompt(
            user_input, 
            contributions, 
            nlp_analysis,
            mood_guidance
        )
        
        # Build conversation messages for LLM (with full history)
        conversation_messages = self._build_conversation_messages(synthesis_prompt)
        
        # Generate final response - ULTRA SHORT for human realism
        resp = self.master_llm.generate(
            synthesis_prompt, 
            max_tokens=120,  # Ultra-short for natural human-like responses
            messages=conversation_messages,
            temperature=0.9
        )
        final_response = self._extract_text(resp)
        
        # Record successful interaction for learning
        self.nlp_context.record_success(
            self.session_id,
            user_input,
            final_response,
            sentiment,
            topics,
            relevant_agent_types
        )
        
        # Add assistant response to memory
        self.memory.add_message('Assistant', final_response, metadata={
            'agents_consulted': relevant_agent_types,
            'assessment_scores': self.assessment_tracker.calculate_scores(),
            'sentiment_score': sentiment.get('score'),
            'emotion': sentiment.get('emotion')
        })
        
        # Save to history
        self.conversation_history.append({
            'user': user_input,
            'agents_consulted': relevant_agent_types,
            'response': final_response,
            'nlp_analysis': nlp_analysis
        })
        
        return {
            'text': final_response,
            'agents_consulted': relevant_agent_types,
            'nlp_analysis': nlp_analysis,  # Include for debug mode
            'contributions': contributions,
            'assessment_summary': self.assessment_tracker.get_assessment_summary(),
            'assessment_analysis': assessment_analysis,
            'mood_guidance': mood_guidance,
            'mood_summary': self.mood_tracker.get_mood_summary(),
            'raw': resp
        }
    
    def _build_synthesis_prompt(self, user_input: str, contributions: List[Dict], 
                               nlp_analysis: Dict = None, mood_guidance: Dict = None) -> str:
        """Build prompt for master agent to synthesize contributions with NLP insights and mood tracking."""
        prompt_parts = [self.master_prompt]
        
        # Add conversation context from memory system
        context = self.memory.get_context_for_llm()
        if context:
            prompt_parts.append(f"\n{context}")
        
        # Add repetition check - what suggestions AND questions were already made
        recent_responses = [msg['content'] for msg in self.memory.get_recent_messages(6) if msg['role'] == 'Assistant']
        if recent_responses:
            suggestions_made = []
            questions_asked = []
            
            for resp in recent_responses:
                resp_lower = resp.lower()
                # Track suggestions
                if 'journal' in resp_lower:
                    suggestions_made.append('journaling')
                if 'walk' in resp_lower or 'exercise' in resp_lower:
                    suggestions_made.append('walking/exercise')
                if 'breath' in resp_lower:
                    suggestions_made.append('breathing exercises')
                if 'therapist' in resp_lower or 'counselor' in resp_lower:
                    suggestions_made.append('professional help')
                if 'friend' in resp_lower or 'talk to' in resp_lower:
                    suggestions_made.append('talking to someone')
                if 'music' in resp_lower:
                    suggestions_made.append('music/creative activities')
                
                # Track repeated question patterns
                if 'what does' in resp_lower and 'mean to you' in resp_lower:
                    questions_asked.append('"what does X mean to you?"')
                if 'how' in resp_lower and 'feel' in resp_lower:
                    questions_asked.append('"how do you feel?"')
                if 'what' in resp_lower and 'been' in resp_lower:
                    questions_asked.append('"what has been happening?"')
                if 'can you tell me' in resp_lower:
                    questions_asked.append('"can you tell me more?"')
            
            if suggestions_made or questions_asked:
                repetition_warning = "\n=== AVOID REPETITION ==="
                if suggestions_made:
                    repetition_warning += f"\nAlready suggested: {', '.join(set(suggestions_made))}"
                if questions_asked:
                    repetition_warning += f"\nAlready asked similar to: {', '.join(set(questions_asked))}"
                repetition_warning += "\n⚠️ DO NOT repeat these. Ask NEW questions or shift the conversation."
                prompt_parts.append(repetition_warning)
        
        # Add background assessment context (invisible to user)
        background_assessment = self.assessment_tracker.get_background_context()
        if background_assessment:
            prompt_parts.append(f"\n{background_assessment}")
        
        # Add mood tracking guidance
        if mood_guidance:
            mood_context = "\n=== MOOD TRACKING GUIDANCE ==="
            mood_context += f"\nCurrent emotion: {mood_guidance.get('current_emotion', 'neutral')}"
            mood_context += f"\nMood trend: {mood_guidance.get('trend', 'stable')}"
            mood_context += f"\nUrgency: {mood_guidance.get('urgency', 'low')}"
            mood_context += f"\nRecommended tone: {mood_guidance.get('tone', 'warm')}"
            mood_context += f"\nRecommended approach: {mood_guidance.get('approach', 'curious')}"
            mood_context += f"\nPriority: {mood_guidance.get('priority', 'connection')}"
            if mood_guidance.get('caution') != 'none':
                mood_context += f"\n⚠️ Caution: {mood_guidance['caution']}"
            if mood_guidance.get('dominant_emotions'):
                mood_context += f"\nDominant emotions in session: {', '.join(mood_guidance['dominant_emotions'])}"
            prompt_parts.append(mood_context)
        
        # Add NLP insights for better response personalization
        if nlp_analysis:
            sentiment = nlp_analysis['sentiment']
            personalization = nlp_analysis['personalization']
            
            nlp_context = "\n=== CONVERSATION INSIGHTS (Internal) ==="
            nlp_context += f"\nPrimary emotion: {sentiment.get('emotion', 'neutral')}"
            if sentiment.get('emotions'):
                nlp_context += f"\nAll emotions detected: {', '.join(sentiment['emotions'])}"
            nlp_context += f"\nUrgency level: {sentiment.get('urgency', 'normal')}"
            
            # Banned phrases enforcement
            nlp_context += "\n\n🚫 NEVER USE: 'It sounds like', 'I can hear', 'When someone', 'It's normal', 'emotional state', 'vulnerability', 'process', 'therapeutic'"
            nlp_context += "\n🚫 NEVER DIAGNOSE: 'depression', 'anxiety', 'dissociation', 'repression', 'PTSD', 'trauma'"
            nlp_context += "\n✅ USE INSTEAD: 'Ouch', 'Damn', 'That's rough', 'I'd feel the same', 'going through tough time', 'feeling down', 'worried'"
            nlp_context += "\n✅ THERAPIST MICRO-SKILLS: 1) Label emotion 2) Normalize it 3) Gentle specific question"
            
            # Context interpretation hints based on detected emotions
            if sentiment.get('emotions'):
                emotions = sentiment['emotions']
                nlp_context += "\n\nEmotion-specific guidance:"
                if 'betrayal' in emotions:
                    nlp_context += "\n- Betrayal: Acknowledge trust violation directly, don't minimize"
                if 'shame' in emotions:
                    nlp_context += "\n- Shame: Normalize, de-stigmatize, validate experience"
                if 'hurt' in emotions:
                    nlp_context += "\n- Hurt: Acknowledge pain, don't rush to fix"
                if 'anger' in emotions:
                    nlp_context += "\n- Anger: Validate as protective response to violation"
                if 'grief' in emotions:
                    nlp_context += "\n- Grief: Honor the loss, don't rush healing"
                if 'loneliness' in emotions:
                    nlp_context += "\n- Loneliness: Acknowledge isolation, be present"
            
            # Context clues from specific words
            nlp_context += "\n\nContext clues:"
            if 'broke' in user_input.lower() or 'smashed' in user_input.lower():
                nlp_context += "\n- Physical destruction = anger release/overwhelm (NOT resilience metaphor)"
            if 'dream' in user_input.lower():
                nlp_context += "\n- Dreams about person = unresolved attachment (address directly)"
            if 'hate' in user_input.lower():
                nlp_context += "\n- 'Hate' = deep hurt underneath (explore hurt, not hate)"
            if 'secret' in user_input.lower() or 'betray' in user_input.lower():
                nlp_context += "\n- Betrayal = trust wound (needs acknowledgment of violation)"
            
            # Extract user's key phrases for mirroring
            recent_user_messages = [msg['content'] for msg in self.memory.get_recent_messages(3) if msg['role'] == 'User']
            if recent_user_messages:
                nlp_context += f"\\nUser's exact words to mirror: {' | '.join(recent_user_messages[-2:])}"
            
            if personalization.get('preferred_tone'):
                nlp_context += f"\\nUser prefers: {personalization['preferred_tone']} tone"
            
            if personalization.get('effective_techniques'):
                nlp_context += f"\nWhat has worked before: {', '.join(personalization['effective_techniques'][:3])}"
            
            if nlp_analysis.get('learned_recommendations'):
                learned = nlp_analysis['learned_recommendations'][:2]  # Top 2
                if learned:
                    nlp_context += "\nSuccessful approaches from past conversations:"
                    for rec in learned:
                        nlp_context += f"\n  - {rec}"
            
            prompt_parts.append(nlp_context)
        
        prompt_parts.append("\n=== CURRENT USER MESSAGE ===")
        prompt_parts.append(user_input)
        
        prompt_parts.append("\n=== EXPERT CONTRIBUTIONS ===")
        for contrib in contributions:
            agent_name = contrib['agent_type'].upper()
            prompt_parts.append(f"\n{agent_name} EXPERT:")
            prompt_parts.append(f"{contrib['contribution']}")
            if contrib.get('context_used'):
                prompt_parts.append(f"(Based on: {', '.join(contrib['context_used'][:2])})")
        
        prompt_parts.append("\n=== YOUR TASK ===")
        
        # Count how many messages in this conversation
        message_count = len(self.memory.messages)
        
        # Detect if user is expressing deep emotion vs asking for help
        user_lower = user_input.lower()
        asking_for_help = any(phrase in user_lower for phrase in [
            'what should i do', 'what can i do', 'help me', 'any advice', 'suggestions', 'what do you think'
        ])
        rejecting_advice = any(phrase in user_lower for phrase in [
            'tried that', 'doesn\'t work', 'not helping', 'already doing', 'i dont like', 'better suggestions'
        ])
        expressing_emotion = any(phrase in user_lower for phrase in [
            'feel', 'miss', 'hurt', 'pain', 'sad', 'scared', 'alone', 'lost', 'empty', 'dream'
        ])
        
        if message_count <= 2:  # First interaction
            prompt_parts.append("""First message - be human.

1-2 sentences max.
Micro-empathy: "That sounds hard." "Ouch."
One tiny question.

NO: "It takes courage", "I hear you", formal validation

Good: "That sounds hard. What's hitting you hardest?"

Your response:""")
        elif expressing_emotion and not asking_for_help:  # User sharing feelings
            # Detect emotional intensity for mirroring
            high_intensity_words = ['hate', 'rage', 'furious', 'can\'t take it', 'breaking', 'destroyed', 'betray']
            medium_intensity_words = ['hurt', 'pain', 'sad', 'miss', 'alone', 'lost']
            
            high_intensity = any(word in user_lower for word in high_intensity_words)
            medium_intensity = any(word in user_lower for word in medium_intensity_words)
            
            if high_intensity:
                prompt_parts.append("""HIGH EMOTION - use therapist micro-skills.

Structure (1-2 sentences):
1. Emotion labeling: "That's [hurt/anger/betrayal]."
2. Normalize: "Makes sense you'd feel that."
3. Maybe pause, maybe tiny question.

Good examples:
"That's betrayal. Makes sense you'd feel that way."
"Ouch. Anyone would be hurt by that."
"Damn. That would hit me hard too."

Your response:""")
            elif medium_intensity:
                prompt_parts.append("""Medium emotion - therapist micro-skills.

Structure (2-3 sentences):
1. Emotion labeling + normalize: "That sounds like grief. It's normal to miss someone."
2. Gentle validation: "Anyone would feel that."
3. Specific gentle question: "What part do you miss most?"

Good: "That sounds like grief. Missing someone you connected with - that's normal. What do you miss most?"

NO clinical terms, NO templates.

Your response:""")
            else:
                prompt_parts.append("""Low emotion - you can explore a bit.

2-3 sentences.
Stay conversational.
No templates.

Your response:""")
        elif rejecting_advice:  # User rejected previous suggestions
            prompt_parts.append("""User rejected advice - acknowledge simply.

"Fair. What would help?"

That's it. No apologies, no essays.

Your response:""")
        elif asking_for_help and message_count >= 6:  # User explicitly asking for help
            prompt_parts.append("""User wants ideas - give them.

1. One line about their situation
2. One specific idea for THEIR context
3. Why it might help

2-3 sentences total.
No generic advice.
Use their words and situation.

Example: "Seeing her daily while healing - that's hard. Could you shift your route to cross paths less? Even small distance helps."

Your response:""")
        else:  # General conversation
            prompt_parts.append("""Keep it real.

1-2 sentences.
Stay human.
No templates.

Your response:""")
        
        return "".join(prompt_parts)
    
    def _build_conversation_messages(self, synthesis_prompt: str) -> list:
        """Build message list with conversation history for LLM."""
        messages = []
        
        # Add system message with master prompt
        messages.append({
            "role": "system",
            "content": self.master_prompt
        })
        
        # Add conversation history (last 10 messages for context)
        recent_messages = self.memory.get_recent_messages(count=10)
        for msg in recent_messages:
            role = "user" if msg['role'] == "User" else "assistant"
            messages.append({
                "role": role,
                "content": msg['content']
            })
        
        # Add current synthesis prompt as user message
        messages.append({
            "role": "user",
            "content": synthesis_prompt
        })
        
        return messages
    
    def _extract_text(self, resp: Dict[str, Any]) -> str:
        """Extract text from LLM response."""
        if isinstance(resp, dict):
            if 'choices' in resp and resp['choices']:
                choice = resp['choices'][0]
                if 'message' in choice:
                    return choice['message'].get('content', '')
                elif 'text' in choice:
                    return choice['text']
            elif 'candidates' in resp and resp['candidates']:
                candidate = resp['candidates'][0]
                if 'content' in candidate:
                    content = candidate['content']
                    if 'parts' in content and content['parts']:
                        return content['parts'][0].get('text', '')
        return str(resp)
