from datetime import datetime

class Conversation:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.scenario_type = None
        self.questions = []
        self.current_question_index = -1
        self.counter=1
        self.responses = {}
        self.scenario_summary = None
        self.updated_summary = None
        self.updated_conversation = None
        self.messages = []
        self.message_db=[]
        self.witness=None
        self.resident_id = None        
        self.resident_name = None        
        self.reporting_person_id = "Agent_01"  
        self.reporting_person = "Luca"     
        self.summary_edited = False
        self.waiting_for_event_type_selection = False
        self.post_event_completed=False
        self.injury_analysis = None
        self.injury_size = None
        self.injury_location = None
        self.initial_Summary = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
