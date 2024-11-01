import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
load_dotenv()


print("transcript url is: ", os.getenv('VOICE_TRANSCRIPT_API_ENDPOINT'))

def load_azure_speech_sdk(conversation_id = "-"):
    # res = voice_rec_comp()
    
    # print('res is: ', res)
    func = "()=>{}"
    if conversation_id != "-":
        func = """() => {
                        
                        
                        
                            const subscriptionKey = '""" + os.getenv("AZURE_SPEECH_KEY") + """';
                            const serviceRegion = '""" + os.getenv("AZURE_SPEECH_REGION") + """';
                            const SpeechSDK = window.SpeechSDK || window.parent.SpeechSDK || globalThis.SpeechSDK;

                            console.log('Starting continuous recognition with silence detection...');

                            const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(subscriptionKey, serviceRegion);
                            speechConfig.speechRecognitionLanguage = "en-US";
                            const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
                            const speechRecognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

                            let silenceTimer;
                            const silenceThreshold = 1000 * 2; //2 seconds
                            const silenceThresholdFirstTime = 1000 * 10; //10 seconds
                            let thresholdNotReset = true;
                            let userResponse = null;

                            // Function to reset the silence timer
                            const resetSilenceTimer = (shouldStop = false) => {
                                if (silenceTimer) clearTimeout(silenceTimer);
                                if(shouldStop){
                                    stopRecognition();
                                    return; 
                                }
                                
                                silenceTimer = setTimeout(() => {
                                    console.log("No voice detected for 2 seconds, stopping recognition.");
                                    stopRecognition();
                                },  thresholdNotReset ? silenceThresholdFirstTime : silenceThreshold);
                                
                                thresholdNotReset = false;
                            };

                            // Function to stop continuous recognition
                            const stopRecognition = () => {
                                speechRecognizer.stopContinuousRecognitionAsync(
                                    () => {
                                        console.log("Continuous recognition stopped.");
                                        fetch(`""" + os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT") + """/set-user-text/?conversation_id="""+conversation_id+"""&text=${userResponse===null? '%20': userResponse}`);
                                    },
                                    (err) => console.error("Error stopping recognition:", err)
                                );
                            };

                            // Event handler for interim recognition results
                            speechRecognizer.recognizing = (sender, event) => {
                                console.log("Interim result:", event.result.text);
                                resetSilenceTimer(); // Reset timer on every recognizing event
                            };

                            // Event handler for final recognition results
                            speechRecognizer.recognized = (sender, event) => {
                                if (event.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
                                    console.log("Final result:", event.result.text);
                                    userResponse =  (userResponse? userResponse : ' ') + event.result.text;
                                    resetSilenceTimer(); 
                                } else {
                                    console.error("Speech not recognized.");
                                    resetSilenceTimer(true);
                                }
                            };

                            // Handle recognition errors
                            speechRecognizer.canceled = (sender, event) => {
                                console.error(`Canceled: ${event.errorDetails}`);
                                resetSilenceTimer(true);
                            };

                            // Start continuous recognition with the silence threshold
                            speechRecognizer.startContinuousRecognitionAsync(
                                () => {
                                    console.log("Continuous recognition started.");
                                    resetSilenceTimer(); // Start the timer as soon as recognition starts
                                },
                                (err) => {
                                    console.error("Error starting continuous recognition:", err);
                                }
                            );


                        }"""
    render_component(func)
    
  

def load_azure_synthetic_speech_sdk(text = "-", conversation_id = '-'):
    func = "()=>{}"
    if text != "-":
        func = """() => {
                            const text = `"""+text+"""`;
                            const subscriptionKey = '""" + os.getenv("AZURE_SPEECH_KEY") + """';
                            const serviceRegion = '""" + os.getenv("AZURE_SPEECH_REGION") + """';
                            
                            const SpeechSDK = window.SpeechSDK || window.parent.SpeechSDK || globalThis.SpeechSDK;
                                    
                            console.log('synthesizing speech now...');
                            
                            const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(subscriptionKey, serviceRegion);

                            
                            speechConfig.speechSynthesisVoiceName = "en-GB-BellaNeural";
                            const audioConfig = SpeechSDK.AudioConfig.fromDefaultSpeakerOutput();
                                                        
                            // Configure speech synthesis
                            const synthesizer = new SpeechSDK.SpeechSynthesizer(speechConfig, audioConfig);
                            
                            synthesizer.speakTextAsync(
                                text,
                                result => {
                                    if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
                                        console.log("Speech synthesized for text: " + text);
                                    } else {
                                        console.error("Error synthesizing speech: ", result.errorDetails);
                                    }
                                    synthesizer.close();
                                    
                                    setTimeout(() => {
                                        fetch(`""" + os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT") + """/set-is-speaking/?conversation_id=""" + conversation_id + """&is_speaking=false`);
                                    }, result.audioDuration / 10000);
                                },
                                error => {
                                    console.error("Error: ", error);
                                    synthesizer.close();
                                    fetch(`""" + os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT") + """/set-is-speaking/?conversation_id=""" + conversation_id + """&is_speaking=false`);
                                }
                            );
                            
                        }"""
    render_component(func)

    
  
def render_component(func):
      components.html(
        """
        <script>
        
            if (!window.parent.AzureSpeechSDK) {
                let sdkScript = document.createElement('script');
                sdkScript.src = "https://aka.ms/csspeech/jsbrowserpackageraw";
                sdkScript.onload = () => {
                    window.parent.AzureSpeechSDK = true;
                    console.log("Azure Speech SDK loaded.");
                    
                     ("""+func+""")();
                    
                    
                    
                }
                
                window.parent.document.head.appendChild(sdkScript);
            } else {
                console.log("Azure Speech SDK already loaded.");
                
                ("""+func+""")();
                
                    
                
            }
            
            
            
        </script>
        """,
        height=0,
        # key="xyz"
    )
