from groq import Groq
import os
import time

class GroqService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def summarize_scenario(self, responses: dict, scenario_type: str) -> str:
        try:
            # Combine the provided Q&A responses into a description
            combined_description = f"This is a report about a {scenario_type}.\n"
            for i, (question, answer) in enumerate(responses.items(), start=1):
                combined_description += f"{i}. {question}: {answer}\n"

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a report writing expert. "
                            "You will always generate the report based strictly on the context provided by the user in a question-and-answer format. "
                            "The report must be descriptive and structured as follows:\n"
                            "1. **Title of the Incident**: Provide a clear, concise title derived from the incident details.\n"
                            "2. **Descriptive Summary**: Craft a detailed paragraph explaining the incident in a narrative form. Ensure the description is vivid and context-specific, including details such as time, location, people involved, and actions taken. Provide a coherent flow that tells the story of what happened step by step.\n"
                            "3. **Key Findings**: Summarize the main facts, extracted directly from the user's input, with key elements such as location, actions, and individuals involved. Bold important facts and findings.\n"
                            "4. **Recommendations**: Provide actionable recommendations directly related to the key findings. Base these recommendations on the context provided. Bold any significant recommendations.\n"
                            "5. **Action Taken**: Describe any actions taken based on the user's input. Highlight any immediate responses or follow-up actions. Bold key actions.\n"
                            "Ensure that no information is added or inferred that is not explicitly stated in the user's input. The narrative and recommendations should be strictly context-based, and all relevant words, findings, and actions should be bolded for emphasis."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Summarization of the following incident or accident:\n{combined_description}"
                    }
                ],
                model="llama-3.1-70b-versatile"
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
                        "You are an expert language model that checks, corrects grammatical errors and converts the sentences to past tense. "
                        "Follow these steps:\n\n"
                        "1. **Analyze the Sentence**: Carefully read the user response and identify any grammatical errors.\n"
                        "2. **Correct Errors**: Fix any grammatical issues such as verb agreement, spelling, or punctuation.\n"
                        "3. **Convert to Past Tense**: Always convert the sentence to past tense, even if it's already grammatically correct.\n"
                        "4. **Preserve Meaning**: Ensure the original meaning of the sentence is maintained.\n"
                        "5. **Generate the Response**: Output only the corrected and past tense version of the sentence.\n"
                        "**Important Notes:**\n"
                        "- Do not provide explanations or additional comments. just provide the context.\n"
                        "- Always convert to past tense, unless dealing with dates, times, or days.\n"
                        "- For single-word responses or short phrases, return them as-is.\n"
                        "Examples:\n"
                        "Input: The patient is experiencing chest pain.\nOutput: The patient was experiencing chest pain.\n"
                        "Input: We administer medication to the patient.\nOutput: We administered medication to the patient.\n"
                        "Input: The incident occurs at 3:00 PM.\nOutput: The incident occurred at 3:00 PM.\n"
                        "Input: IPC related\nOutput: IPC related\n"
                        "Input: missing person\nOutput: missing person\n"
                        "Input: self harm\nOutput: self harm\n"
                        "Input: physical assault\nOutput: physical assault\n"
                    )
                    },
                    {
                        "role": "user",
                        "content": user_response.strip() 
                    }
                ],
                
                model="llama3-8b-8192"
            )
 
            corrected_response = response.choices[0].message.content.strip()
            print('corrected_response',corrected_response)
 
            if corrected_response == user_response:
                return user_response
 
            return corrected_response
 
        except Exception as e:
            print(f"Error refining response: {e}")
            return "An error occurred during grammatical correction."