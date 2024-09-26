from groq import Groq
import os
import time

class GroqService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def summarize_scenario(self, responses: dict, scenario_type: str) -> str:
        try:
            combined_description = f"This is a report about a {scenario_type}."
            for i, (question, answer) in enumerate(responses.items(), start=1):
                combined_description += f"{i}. {question}: {answer}\n"
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a report writing expert. "
                                                  "You always generate the report as a paragraph based on question and answer scenario"
                                                  "You should generate report as a storyline"
                                                  "You should generate key findings"
                                                  "You should bold the key words and lines in the report."},
                    {"role": "user", "content": f"Summarization of the  the following incident or accident: {combined_description}"}
                ],
                model="llama3-8b-8192"
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error summarizing scenario: {e}")
            return "An error occurred during scenario summarization."
        
    def check_grammar(self, user_response: str) -> str:
        try:
            if not user_response.strip():
                return ""
            
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert language model that checks and corrects user sentences for grammatical errors without altering the sentence structure or meaning."
                            "Follow these steps:\n\n"
                            "1. **Analyze the Sentence**: Carefully read the user response and identify any grammatical errors such as incorrect verb forms, punctuation, or common word misplacements.\n"
                            "2. **Check for Correctness**: If the sentence is grammatically correct, return the response exactly as it is, without any additional comments or changes. "
                            "If there are minor grammatical errors, proceed to the next step.\n"
                            "3. **Correct Minor Errors**: Make small adjustments such as fixing verb agreement, spelling, or punctuation. "
                            "Do not change the sentence structure, logic, or add any new content.\n"
                            "4. **Generate the Response**: If the sentence was correct, return the original sentence. "
                            "If corrections were needed, output only the corrected sentence without adding any text before or after. "
                            "**Do not provide any explanations, additional comments, or the phrase 'Here is the corrected sentence.' Only return the corrected version of the sentence itself.**"
                            "5. **Transform to Past Tense**: Convert the sentence into past tense without altering its original meaning.\n"
                            "**Transform the sentence into past tense if its in other tense**"
                            "**Don't change anything for date, time and day**"
                            "Examples:\n"
                            "Question: What immediate actions were taken after the incident?\nResponse: We calls for medical help.\nOutput: We called for medical help.\n"
                            "Question: Can you tell me what category of incident this was? Here are some options: Was it related to behaviour, medication, a medical issue, the environment, absconding, sexual assault, infection control, self-harm, a missing person, a near miss or others.\nResponse: sexual assault.\nOutput: sexual assault.\n"
                            "Question: What actions were taken right after the incident? For example, was first aid given, the police called, the fire service involved, an ambulance needed, or were neuro observations done ?\nResponse: an ambulance needed.\nOutput: an ambulance needed.\n"
                            "Question: What kind of interventions were used during the incident? Did you give a verbal prompt, use physical intervention or holds, provide PRN medication, or others. ?\nResponse: verbal prompt, PRN medication .\nOutput: verbal prompt, PRN medication. \n"
                            
                    )
                    },
                    {
                        "role": "user",
                        "content": user_response.strip() 
                    }
                ],
                
                model="llama3-8b-8192"
            )
 
            # Extract and return the corrected response
            corrected_response = response.choices[0].message.content.strip()
 
            # If no changes were made, return the original response
            if corrected_response == user_response:
                return user_response
 
            return corrected_response
 
        except Exception as e:
            print(f"Error refining response: {e}")
            return "An error occurred during grammatical correction."