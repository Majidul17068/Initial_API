from datetime import datetime

class Conversation:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.scenario_type = None
        self.questions = []
        self.current_question_index = -1
        self.responses = {}
        self.scenario_summary = None
        self.messages = []
        self.resident_id = "Res_01"         
        self.resident_name = "John Smith"        
        self.reporting_person_id = "Agent_01"  
        self.reporting_person = "Luca"     
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
