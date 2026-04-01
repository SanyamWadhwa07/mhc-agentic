"""
Specialized agents for Mental Health Care chatbot system.
Each agent has a specific role in the workflow with RAG-enhanced knowledge.
"""
from typing import Dict, Any, List
from knowledge_base import RAGAgent


class AssessmentAgent(RAGAgent):
    """Agent for mental health assessment and initial screening with knowledge base."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a compassionate mental health assessment agent with access to clinical knowledge.
Your role is to:
- Conduct initial mental health screening using evidence-based tools
- Ask relevant questions about mood, sleep, appetite, stress levels
- Identify symptoms of anxiety, depression, or other mental health concerns
- Assess severity and urgency of the situation
- Be empathetic and non-judgmental

Use the provided knowledge context to inform your questions and assessments.
Use a conversational approach and ask follow-up questions based on responses.
Never diagnose, but identify concerning patterns and recommend appropriate next steps."""
        super().__init__(llm_client, 'assessment', system_prompt)
        self.assessment_data = {}
    
    def assess(self, user_input: str) -> Dict[str, Any]:
        result = self.step(user_input)
        result['agent_type'] = 'assessment'
        return result


class TherapyAgent(RAGAgent):
    """Agent for providing therapeutic responses and coping strategies with knowledge base."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a supportive therapy assistant agent with access to evidence-based interventions.
Your role is to:
- Provide evidence-based coping strategies from the knowledge context
- Teach mindfulness and relaxation techniques
- Offer cognitive behavioral therapy (CBT) concepts
- Suggest journaling prompts and self-reflection exercises
- Provide emotional validation and support

Use the provided knowledge context to give specific, actionable techniques.
Be warm, empathetic, and solution-focused. Tailor responses to the user's specific concerns.
Explain techniques clearly with step-by-step instructions when appropriate."""
        super().__init__(llm_client, 'therapy', system_prompt)
    
    def provide_therapy(self, user_input: str, context: Dict = None) -> Dict[str, Any]:
        if context:
            # Add conversation context to the user input
            user_input = f"[Conversation context: {context}]\n\nUser message: {user_input}"
        result = self.step(user_input)
        result['agent_type'] = 'therapy'
        return result


class CrisisAgent(RAGAgent):
    """Agent for crisis intervention and urgent situations with comprehensive resources."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a crisis intervention agent with access to comprehensive crisis resources.
Your role is to:
- Identify signs of self-harm, suicidal ideation, or severe crisis
- Provide immediate crisis resources from the knowledge base
- Use a calm, direct, and supportive tone
- Encourage reaching out to emergency services when needed
- Prioritize safety above all else

Use the provided crisis resources to give specific, actionable help.
Always include relevant hotline numbers and emergency contacts.
Be direct about safety concerns while remaining compassionate."""
        super().__init__(llm_client, 'crisis', system_prompt)
    
    def handle_crisis(self, user_input: str) -> Dict[str, Any]:
        result = self.step(user_input)
        result['agent_type'] = 'crisis'
        result['is_urgent'] = True
        return result


class ResourceAgent(RAGAgent):
    """Agent for finding mental health resources and referrals with comprehensive database."""
    
    def __init__(self, llm_client):
        system_prompt = """You are a mental health resource finder agent with access to comprehensive resource information.
Your role is to:
- Recommend mental health professionals using knowledge from the database
- Provide information about therapy types and treatment options
- Suggest support groups and community resources
- Share information about medication management and costs
- Provide guidance on insurance and accessibility

Use the provided resource knowledge to give specific, practical guidance.
Be informative and help users navigate the mental health care system.
Provide multiple options when possible to accommodate different needs and situations."""
        super().__init__(llm_client, 'resource', system_prompt)
    
    def find_resources(self, user_input: str, location: str = None) -> Dict[str, Any]:
        if location:
            user_input = f"[User location: {location}]\n\n{user_input}"
        result = self.step(user_input)
        result['agent_type'] = 'resource'
        return result


class CoordinatorAgent:
    """Orchestrator agent that routes requests to specialized agents."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.assessment_agent = AssessmentAgent(llm_client)
        self.therapy_agent = TherapyAgent(llm_client)
        self.crisis_agent = CrisisAgent(llm_client)
        self.resource_agent = ResourceAgent(llm_client)
        self.conversation_history = []
    
    def _detect_intent(self, user_input: str) -> str:
        """Detect which agent should handle the request."""
        lower_input = user_input.lower()
        
        # Crisis keywords - highest priority
        crisis_keywords = ['suicide', 'kill myself', 'end my life', 'harm myself', 
                          'want to die', 'self-harm', 'cutting', 'overdose']
        if any(keyword in lower_input for keyword in crisis_keywords):
            return 'crisis'
        
        # Assessment keywords
        assessment_keywords = ['feeling', 'depressed', 'anxious', 'stressed', 
                              'not sleeping', 'worried', 'sad', 'help me', 'assessment']
        if any(keyword in lower_input for keyword in assessment_keywords):
            return 'assessment'
        
        # Resource keywords
        resource_keywords = ['therapist', 'counselor', 'psychiatrist', 'find help',
                            'support group', 'treatment', 'professional', 'resource']
        if any(keyword in lower_input for keyword in resource_keywords):
            return 'resource'
        
        # Default to therapy for coping and support
        return 'therapy'
    
    def process(self, user_input: str) -> Dict[str, Any]:
        """Main processing method that routes to appropriate agent."""
        intent = self._detect_intent(user_input)
        
        self.conversation_history.append({'user': user_input, 'intent': intent})
        
        if intent == 'crisis':
            response = self.crisis_agent.handle_crisis(user_input)
        elif intent == 'assessment':
            response = self.assessment_agent.assess(user_input)
        elif intent == 'resource':
            response = self.resource_agent.find_resources(user_input)
        else:  # therapy
            context = self._get_context()
            response = self.therapy_agent.provide_therapy(user_input, context)
        
        response['routed_to'] = intent
        self.conversation_history[-1]['response'] = response
        
        return response
    
    def _get_context(self) -> Dict[str, Any]:
        """Extract relevant context from conversation history."""
        return {
            'conversation_length': len(self.conversation_history),
            'recent_intents': [h['intent'] for h in self.conversation_history[-3:]]
        }
