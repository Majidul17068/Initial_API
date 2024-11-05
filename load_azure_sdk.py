import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
from services.api_service import reset_user_transcript
load_dotenv()


print("transcript url is: ", os.getenv('VOICE_TRANSCRIPT_API_ENDPOINT'))

def load_azure_speech_sdk(conversation_id = "-"):
    # res = voice_rec_comp()
    reset_user_transcript(conversation_id)
    
    # print('res is: ', res)
    func = "()=>{}"
    if conversation_id != "-":
        func = """() => {
                        
                        
                        
                            const subscriptionKey = '""" + os.getenv("AZURE_SPEECH_KEY") + """';
                            const serviceRegion = '""" + os.getenv("AZURE_SPEECH_REGION") + """';
                            const SpeechSDK = window.SpeechSDK || window.parent.SpeechSDK || globalThis.SpeechSDK;

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
                                    stopRecognition();
                                },  thresholdNotReset ? silenceThresholdFirstTime : silenceThreshold);
                                
                                thresholdNotReset = false;
                            };

                            // Function to stop continuous recognition
                            const stopRecognition = () => {
                                speechRecognizer.stopContinuousRecognitionAsync(
                                    () => {
                                        fetch(`""" + os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT") + """/set-user-text/?conversation_id="""+conversation_id+"""&text=${userResponse===null? '%20': userResponse}`);
                                    },
                                    (err) => console.error("Error stopping recognition:", err)
                                );
                            };

                            // Event handler for interim recognition results
                            speechRecognizer.recognizing = (sender, event) => {
                                resetSilenceTimer(); // Reset timer on every recognizing event
                            };

                            // Event handler for final recognition results
                            speechRecognizer.recognized = (sender, event) => {
                                if (event.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
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
                                    
                            
                            const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(subscriptionKey, serviceRegion);

                            
                            speechConfig.speechSynthesisVoiceName = "en-GB-BellaNeural";
                            const audioConfig = SpeechSDK.AudioConfig.fromDefaultSpeakerOutput();
                                                        
                            // Configure speech synthesis
                            const synthesizer = new SpeechSDK.SpeechSynthesizer(speechConfig, audioConfig);
                            
                            synthesizer.speakTextAsync(
                                text,
                                result => {
                                   if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
                                    } else {
                                        console.error("Error synthesizing speech: ", result.errorDetails);
                                    }
                                    synthesizer.close();
                                    
                                    setTimeout(() => {
                                        fetch(`""" + os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT") + """/set-is-speaking/?conversation_id=""" + conversation_id + """&is_speaking=false`);
                                    }, (result.audioDuration / 10000) - (1000 * 2.75 ));
                                },
                                error => {
                                    console.error("Error: ", error);
                                    synthesizer.close();
                                    fetch(`""" + os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT") + """/set-is-speaking/?conversation_id=""" + conversation_id + """&is_speaking=false`);
                                }
                            );
                            
                        }"""
    render_component(func)
    
def _js_hide_or_show_st_element(): 
    # return ''
    return """(()=>{const containers = window.parent.document.querySelectorAll('.stElementContainer');
                    containers.forEach((container) => {
                        
                        container.style.display = 'visible';
                        
                        try {
                           const iframe = container.querySelector('iframe');
                            
                            if (iframe) { // Check if iframe exists
                                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                
                                if (iframeDoc.body.classList.contains('should-hide')) {
                                container.style.display = 'none';
                                }
                            }
                        } catch (error) {
                            console.warn('Cannot access iframe due to cross-origin restrictions', error);
                        }
                        
                        return false;
                        
                    });
                
                })()
                """
  
def hideOrShowStElement():
    components.html("""
                    <script>   
                        window.addEventListener('DOMContentLoaded', () => {
                            document.body.classList.add('should-hide');
                            """+_js_hide_or_show_st_element()+"""
                        });
                    </script>
                    """, height=0, width=0)

def render_component(func):
    components.html(
        """<script>
        
           /* 
            window.addEventListener('DOMContentLoaded', () => {
                document.body.classList.add('should-hide');
                """+_js_hide_or_show_st_element()+"""
            });
                */
        
            if (!window.parent.AzureSpeechSDK) {
                let sdkScript = document.createElement('script');
                sdkScript.src = "https://aka.ms/csspeech/jsbrowserpackageraw";
                sdkScript.onload = () => {
                    window.parent.AzureSpeechSDK = true;
                    ("""+func+""")();
                };
                window.parent.document.head.appendChild(sdkScript);
            } else {
                ("""+func+""")();
            }
        </script>
        """,
        height=0,
        width=0
    )

