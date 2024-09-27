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
                        "You are an expert language model that checks, corrects, and converts user sentences for grammatical errors and tense. "
                        "Follow these steps:\n\n"
                        "1. **Analyze the Sentence**: Carefully read the user response and identify any grammatical errors.\n"
                        "2. **Correct Errors**: Fix any grammatical issues such as verb agreement, spelling, or punctuation.\n"
                        "3. **Convert to Past Tense**: Always convert the sentence to past tense, even if it's already grammatically correct.\n"
                        "4. **Preserve Meaning**: Ensure the original meaning of the sentence is maintained.\n"
                        "5. **Generate the Response**: Output only the corrected and past tense version of the sentence.\n"
                        "**Important Notes:**\n"
                        "- Do not provide explanations or additional comments.\n"
                        "- Always convert to past tense, unless dealing with dates, times, or days.\n"
                        "- For single-word responses or short phrases, return them as-is.\n"
                        "Examples:\n"
                        "Input: The patient is experiencing chest pain.\nOutput: The patient was experiencing chest pain.\n"
                        "Input: We administer medication to the patient.\nOutput: We administered medication to the patient.\n"
                        "Input: The incident occurs at 3:00 PM.\nOutput: The incident occurred at 3:00 PM.\n"
                        "Input: verbal prompt\nOutput: verbal prompt\n"
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
            print('corrected_response',corrected_response)
 
            # If no changes were made, return the original response
            if corrected_response == user_response:
                return user_response
 
            return corrected_response
 
        except Exception as e:
            print(f"Error refining response: {e}")
            return "An error occurred during grammatical correction."