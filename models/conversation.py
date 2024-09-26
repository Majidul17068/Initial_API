class Conversation:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.current_question_index = 0
        self.responses = {}
        self.scenario_type = None
        self.questions = []
        self.scenario_summary = None
        self.unanswered_questions = []
        self.waiting_for_confirmation_step = None
        
