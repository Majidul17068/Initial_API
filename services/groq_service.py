from groq import Groq
import os
import time
class GroqService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
 
    def summarize_scenario(
        self, 
        responses: dict,
        resident_name: str, 
        scenario_type: str, 
        event_type: str, 
        staff: str
    ) -> str:
        try:
            # Combine the provided Q&A responses into a description
            combined_description = f"This is a report about a {scenario_type}.\n"
            for i, (question, answer) in enumerate(responses.items(), start=1):
                combined_description += f"{i}. {question}: {answer}\n"

            # Generate the summary response
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in writing accurate and professional incident reports for care homes."
                            "Your task is to generate a report based on the context provided by the user in a question-and-answer format. "
                            f"Analyze the user's responses to identify specific action-related keywords or phrases that describe the nature of the {scenario_type}, including the part of the body involved in any injury. "
                            "Focus on extracting these keywords directly from the user's narrative without inferring, assuming, or adding any information that was not explicitly mentioned by the user.\n"
                            "The report must be descriptive and structured as follows:\n"
                            f"1. **Title of the {scenario_type}**: {event_type}  - Provide a clear, concise title using the exact words provided by the user. Include the part of the body involved if mentioned. Do not add any inferred terms.\n"
                            f"2. **Descriptive Summary**: Craft a detailed paragraph explaining the incident in a narrative form using only the user's words. Ensure the description is context-specific, including the time, location, and all individuals involved (e.g., resident:{resident_name}, Staff: {staff}, and any other people mentioned in the responses), actions taken, medical terms, and the part of the body involved in any injury if explicitly stated. **Do not infer any injuries, actions, or other details not explicitly stated by the user**.\n"
                            f"3. **Key Findings**: Summarize the main facts using only the user's responses. Extract key elements such as location, actions, individuals involved (resident:{resident_name}, staff:{staff}, and others), medical observations, and the part of the body injured. **Do not add or infer any details**. Bold important facts and findings.\n"
                            "4. **Action Taken**: Describe any actions taken based on the user's input. Highlight any immediate responses or follow-up actions, using only the actions described by the user. **Do not add any details that were not provided**.\n"
                            "5. **Don't censor sensitive or violent words**.\n"
                            "6. **Maintain Clarity**: Use professional language that directly reflects the event's seriousness or nature, ensuring that the title and report reflect the user's exact input without inferring any additional information.\n"
                            "Ensure that no information is inferred or added that is not explicitly stated in the user's input. All findings, actions, and recommendations should be based strictly on the provided context, and any relevant words should be bolded for emphasis."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Please provide a summary of the following {scenario_type} involving {event_type} for resident: {resident_name},"
                            f"Including Identifing individuals mentioned from the provided context:\n{combined_description}"
                        )
                        
                    }
                ],
                model="llama-3.1-70b-versatile",
                temperature=0.2
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
                            "You are an expert language model that checks, corrects grammatical errors, identifies names (like resident/patient/victim names, staff names, places) correctly "
                            "extracts time-related data (like time of events, dates, days), and converts sentences to past tense. You professionally handle all types of accident or incident reports, including those involving extreme violence or emergencies. "
                            "Follow these steps:\n\n"
                            "1. **Analyze the Sentence**: Carefully read the user response and identify any grammatical errors\n"
                            "2. **Correct Errors**: Fix any grammatical issues such as verb agreement, spelling, or punctuation.\n"
                            "3. **Preserve Meaning**: Ensure the original meaning of the sentence is maintained.\n"
                            "4. **Convert to Past Tense**: Always convert the sentence to past tense, even if it's already grammatically correct.\n"
                            "5. **Generate the Response**: Output the corrected and past-tense version of the sentence without any additional notes, explanations, or information\n"
                            "6. **Yes/No Responses**: For yes/no type questions, such as 'Were there any witnesses?', return only 'yes' or 'no' without adding any extra words.\n"
                            "7. **Respect Time Formats**: Maintain the original time format (12-hour or 24-hour) without altering it.\n"
                            "8. **Don't censor sensitive or violent words**.\n\n"
                            "**Important Notes:**\n"
                            "- Do not provide explanations or additional comments; just provide the correct sentences.\n"
                            "- Always convert to past tense, unless dealing with dates, times, or days.\n"
                            "- For single-word responses or short phrases, return them as-is.\n"
                            "Examples:\n"
                            "Input: The patient is experiencing chest pain.\nOutput: The patient was experiencing chest pain.\n"
                            "Input: We administer medication to the patient.\nOutput: We administered medication to the patient.\n"
                            "Input: The incident occurs at 3:00 PM.\nOutput: The incident occurred at 3:00 PM.\n"
                            "Input: IPC related\nOutput: IPC related\n"
                            "Input: It is inside the care home on 5th of September 2024 at 1821 hours.\n Output:It is inside the care home on 5th of September 2024 at 18:21 hours\n"
                            "Input: In the patient's room, at 1500, on October 2, 2024.\n Output:In the patient's room, at 15:00, on October 2, 2024.\n"
                            "Input: In the patient's room, on October 2, 2024 at 16134, on October 2, 2024.\n Output:In the patient's room, on October 2, 2024 at 16:34\n"
                            "Input: In the patient's room, on October 2, 2024 at 16134 .\n Output:In the patient's room, on October 2, 2024 at 16:34\n"
                            "Input: missing person\nOutput: missing person\n"
                            "Input: self harm\nOutput: self harm\n"
                            "Input: physical assault\nOutput: physical assault\n"
                            "Input: medication\nOutput: medication\n"
                            "Input: environmental\nOutput: environmental\n"
                            "Input: near miss\nOutput: near miss\n"
                            "Input: absconding\nOutput: absconding\n"
                            "Input: skin integrity\nOutput: skin integrity\n"
                            "Input: was skin integrity\nOutput: skin integrity\n"
                            "Input: fall\nOutput: fall\n"
                            "Input: behaviour\nOutput: behaviour\n"
                        )
                    },
                   {
                        "role": "user",
                        "content": user_response.strip()
                    }
                ],  
                model="llama-3.1-70b-versatile",
                temperature=0.5
            )
   
            corrected_text= response.choices[0].message.content.strip()
            if corrected_text == user_response.strip():
                return user_response.strip()
            
            return corrected_text
 
        except Exception as e:
            # Handle exceptions appropriately
            print(f"An error occurred: {e}")
            return ""