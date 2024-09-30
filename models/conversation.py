class Conversation:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.scenario_type = None  # 'incident' or 'accident'
        self.questions = []
        self.current_question_index = -1
        self.responses = {}
        self.scenario_summary = None