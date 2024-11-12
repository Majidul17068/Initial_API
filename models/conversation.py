from datetime import datetime

class Conversation:
    def __init__(self, conversation_id):
        # Core conversation identifiers
        self.conversation_id = conversation_id
        self.resident_id = None        
        self.resident_name = None        
        self.reporting_person_id = "Agent_01"  
        self.reporting_person = "Luca"     
        
        # Conversation flow control
        self.scenario_type = None  # 'incident' or 'accident'
        self.questions = []
        self.current_question_index = -1
        self.counter = 1
        self.waiting_for_event_type_selection = False
        
        # Response tracking
        self.responses = {}
        self.messages = []
        self.message_db = []
        self.witness = None
        self.event_type = None
        
        # Summary management
        self.scenario_summary = None
        self.updated_summary = None
        self.summary_edited = False
        self.updated_conversation = None
        
        # Injury tracking
        self.injury_details = {
            'analysis_result': None,            # Complete analysis result from GroqService
            'has_injury_risk': False,           # Whether there's a risk of injury
            'injury_mentioned': False,          # Whether injury was mentioned in details
            'injury_confirmed': None,           # User's confirmation of injury
            'injury_size': None,                # Selected injury size
            'injury_location': None,            # Described injury location
            'risk_level': None,                 # Percentage risk from analysis
            'risk_reasoning': None,             # Explanation of risk assessment
            'mention_details': None,            # Details of injury mentions found
            'questions_asked': {                # Track which injury questions were asked
                'confirmation': False,
                'size': False,
                'location': False
            }
        }
        
        # State management
        self.post_event_completed = False
        
        # Timestamps
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_injury_analysis(self, analysis_result):
        """Updates injury details based on event analysis"""
        self.injury_details.update({
            'analysis_result': analysis_result,
            'has_injury_risk': analysis_result.get('has_injury', False),
            'injury_mentioned': analysis_result.get('injury_mentioned', False),
            'risk_level': analysis_result.get('likelihood', 0),
            'risk_reasoning': analysis_result.get('reasoning', ''),
            'mention_details': analysis_result.get('mention_details', 'None found')
        })
        # Update scenario type based on analysis if available
        if 'classification' in analysis_result:
            self.scenario_type = analysis_result['classification']

    def set_injury_confirmation(self, confirmed: bool):
        """Records the user's confirmation of injury"""
        self.injury_details['injury_confirmed'] = confirmed
        self.injury_details['questions_asked']['confirmation'] = True

    def set_injury_size(self, size: str):
        """Records the injury size"""
        self.injury_details['injury_size'] = size
        self.injury_details['questions_asked']['size'] = True

    def set_injury_location(self, location: str):
        """Records the injury location"""
        self.injury_details['injury_location'] = location
        self.injury_details['questions_asked']['location'] = True

    @property
    def needs_injury_confirmation(self) -> bool:
        """Determines if injury confirmation question is needed"""
        if self.injury_details['has_injury_risk']:
            return not self.injury_details['injury_mentioned'] and not self.injury_details['questions_asked']['confirmation']
        return False

    @property
    def needs_injury_details(self) -> bool:
        """Determines if injury size/location questions are needed"""
        if self.injury_details['injury_mentioned']:
            return True
        return (self.injury_details['injury_confirmed'] and 
                not all([self.injury_details['questions_asked']['size'],
                        self.injury_details['questions_asked']['location']]))

    def get_injury_summary(self) -> str:
        """Returns a formatted summary of injury details"""
        if not self.injury_details['has_injury_risk']:
            return "No injury risk identified."
        
        summary_parts = []
        if self.injury_details['injury_size']:
            summary_parts.append(f"Size: {self.injury_details['injury_size']}")
        if self.injury_details['injury_location']:
            summary_parts.append(f"Location: {self.injury_details['injury_location']}")
        
        if summary_parts:
            return f"Injury details - {', '.join(summary_parts)}"
        return "Injury details pending assessment."

    def to_dict(self) -> dict:
        """Converts conversation state to dictionary for storage"""
        return {
            "conversation_id": self.conversation_id,
            "scenario_type": self.scenario_type,
            "resident_id": self.resident_id,
            "resident_name": self.resident_name,
            "event_type": self.event_type,
            "reporting_agent_id": self.reporting_person_id,
            "reporting_agent": self.reporting_person,
            "messages": self.message_db,
            "injury_details": self.injury_details,
            "updated_conversation": self.updated_conversation,
            "summary": self.scenario_summary,
            "post_event_completed": self.post_event_completed,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
