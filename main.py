import base64
import json
import os
from flask import Flask, request, Response
from flask_sock import Sock
from twilio.rest import Client
from dotenv import load_dotenv
from queue import Queue , Empty
import threading
import time
import requests
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)



load_dotenv()

# Flask settings
PORT = 5000
DEBUG = False
INCOMING_CALL_ROUTE = '/'
WEBSOCKET_ROUTE = '/realtime'

# Twilio authentication
account_sid = os.environ['TWILIO_ACCOUNT_SID']
api_key = os.environ['TWILIO_API_KEY_SID']
api_secret = os.environ['TWILIO_API_SECRET']
client = Client(api_key, api_secret, account_sid)
TWILIO_NUMBER = os.environ['TWILIO_NUMBER']

# Deepgram settings
DEEPGRAM_API_KEY = os.environ['DEEPGRAM_API_KEY']

# Endpoint for RAG query
RAG_QUERY_URL = 'http://127.0.0.1:5001/rag_query'

app = Flask(__name__)
sock = Sock(app)

# Global variables for managing state
audio_queue = Queue()
call_active = threading.Event()
deepgram_connection = None
lock_exit = threading.Lock()
exit_flag = False
transcript = ""
response_to_speak = None  # Variable to hold the response to speak
current_call_sid = None

def send_transcript_to_rag_query(final_transcript):
    """Send transcript to RAG query endpoint"""
    try:


        callwise_api = os.getenv('CALLWISE_API')  # Make sure 'callwise_api' is set in your environment
       
        if callwise_api is None:
            print("Error: CALLWISE_API environment variable is not set.")
            return None

        # Prepare payload with conversation history
        payload = {
            "user_id": callwise_api,  # Replace with actual user ID
            "query": final_transcript,
            "conversation_history": []  # Add conversation history if needed
        }

        response = requests.post(RAG_QUERY_URL, json=payload)

        if response.status_code == 200:
            output = response.json().get("response", "No response")
            print("RAG Response:", output)
            return output
        else:
            print("Error:", response.json())
            return None
    except Exception as e:
        print(f"Error sending to RAG query: {e}")
        return None

def setup_deepgram():
    """Set up the Deepgram connection"""
    try:
        # Create Deepgram client
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create websocket connection
        connection = deepgram.listen.live.v("1")
        
        # Define event handlers
        def on_message(self, result, **kwargs):
            global transcript, response_to_speak
            transcript = result.channel.alternatives[0].transcript
            if transcript.strip():
                print(f"Transcript: {transcript}")
                
                # Send transcript to RAG query immediately
                rag_response = send_transcript_to_rag_query(transcript)
                
                if rag_response:
                    # Set the response to speak
                    response_to_speak = rag_response

        def on_metadata(self, metadata, **kwargs):
            print(f"Metadata: {metadata}")
        
        def on_error(self, error, **kwargs):
            print(f"Error: {error}")
        
        # Register event handlers
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
        connection.on(LiveTranscriptionEvents.Error, on_error)
        
        # Configure Deepgram options
        options = LiveOptions(
            model="nova-2",
            language="en-IN",
            encoding="mulaw",
            sample_rate=8000,
            smart_format=True,
            interim_results=False,
            punctuate=True,
        )
        
        # Start the connection
        connection.start(options)
        print("Successfully connected to Deepgram")
        return connection
        
    except Exception as e:
        print(f"Error setting up Deepgram: {e}")
        return None

def process_audio_queue():
    """Process audio data from the queue and send to Deepgram"""
    global deepgram_connection, exit_flag, call_active
    
    try:
        silence_data = b'\xff' * 160  # mu-law encoded silence
        last_audio_time = time.time()
        
        while call_active.is_set() or not audio_queue.empty():
            try:
                audio_data = audio_queue.get(timeout=0.1)
                if audio_data is None:
                    break
                
                lock_exit.acquire()
                if exit_flag:
                    lock_exit.release()
                    break
                lock_exit.release()
                
                current_time = time.time()
                # Send silence if more than 100ms has passed without audio
                if current_time - last_audio_time > 0.1:
                    deepgram_connection.send(silence_data)
                
                deepgram_connection.send(audio_data)
                last_audio_time = current_time
                time.sleep(0.01)  # Small delay to prevent overwhelming the connection
                
            except Empty:
                # Send silence if queue is empty
                deepgram_connection.send(silence_data)
                last_audio_time = time.time()
            except Exception as e:
                print(f"Error sending audio to Deepgram: {e}")
                break
    except Exception as e:
        print(f"Error processing audio queue: {e}")
    finally:
        try:
            if deepgram_connection:
                deepgram_connection.finish()
        except:
            pass


@app.route(INCOMING_CALL_ROUTE, methods=['GET', 'POST'])
def receive_call():
    """Handle incoming Twilio calls"""
    global current_call_sid  # Ensure this is global
    if request.method == 'POST':
        current_call_sid = request.values.get('CallSid')  # Store CallSid here
        if not current_call_sid:
            print("Error: CallSid not found.")
        
        xml = f"""
<Response>
    <Say>
        Start speaking.
    </Say>
    <Connect>
        <Stream url='wss://{request.host}{WEBSOCKET_ROUTE}' />
    </Connect>
</Response>
""".strip()
        return Response(xml, mimetype='text/xml')
    else:
        return "Real-time phone call transcription service"
    
@sock.route(WEBSOCKET_ROUTE)
def handle_twilio_connection(ws):
    """Handle WebSocket connection from Twilio"""
    global deepgram_connection, exit_flag, response_to_speak, call_active
    
    print("New Twilio WebSocket connection established")
    
    # Set up Deepgram connection
    call_active.set()
    deepgram_connection = setup_deepgram()
    if not deepgram_connection:
        print("Failed to establish Deepgram connection")
        return
    
    # Start audio processing thread
    audio_thread = threading.Thread(target=process_audio_queue)
    audio_thread.daemon = True
    audio_thread.start()
    
    try:
        last_activity_time = time.time()
        while call_active.is_set():  # Change to use call_active event
            try:
                # Use a timeout to periodically check call_active
                message = ws.receive(timeout=5)  # Add timeout
                
                if message is None:
                    # Check if call is still active
                    if not call_active.is_set():
                        break
                    continue
                
                data = json.loads(message)
                match data['event']:
                    case "connected":
                        print('Twilio WebSocket connected')
                        last_activity_time = time.time()
                    case "start":
                        print('Call started')
                        last_activity_time = time.time()
                    case "media":
                        try:
                            payload_b64 = data['media']['payload']
                            audio_data = base64.b64decode(payload_b64)
                            audio_queue.put(audio_data)
                            last_activity_time = time.time()
                        except Exception as e:
                            print(f"Error processing media: {e}")
                    case "stop":
                        print('Call stop event received')
                        call_active.clear()
                        break

                # Handle response to speak
                if response_to_speak:
                    try:
                        client.calls(current_call_sid).update(
                            twiml=f"""
                            <Response>
                                <Pause length="1"/>
                                <Say>Just a Second looking for the information</Say>
                                <Say>{response_to_speak}</Say>
                                <Pause length="1"/>
                                <Say>Please continue speaking.</Say>
                                <Connect>
                                    <Stream url='wss://{request.host}{WEBSOCKET_ROUTE}' />
                                </Connect>
                            </Response>
                            """
                        )
                        print("Spoken response sent via Twilio")
                        response_to_speak = None
                    except Exception as e:
                        print(f"Error speaking response: {e}")

                # Periodic keep-alive check
                if time.time() - last_activity_time > 30:  # 30 seconds inactivity
                    try:
                        client.calls(current_call_sid).update(
                            twiml="""
                            <Response>
                                <Pause length="1"/>
                                <Say>Still here and listening.</Say>
                                <Connect>
                                    <Stream url='wss://{request.host}{WEBSOCKET_ROUTE}' />
                                </Connect>
                            </Response>
                            """
                        )
                        print("Sent keep-alive message to Twilio")
                        last_activity_time = time.time()
                    except Exception as e:
                        print(f"Error sending keep-alive message: {e}")

            except websocket.WebSocketTimeoutException:
                # Timeout occurred, but we want to continue
                if not call_active.is_set():
                    break
                continue
            except Exception as e:
                print(f"WebSocket receive error: {e}")
                break

    except Exception as e:
        print(f"Error in Twilio connection: {e}")
    finally:
        print("Cleaning up connections...")
        
        # Signal threads to stop
        call_active.clear()
        
        # Clean up queue
        audio_queue.put(None)
        
        # Wait for audio processing to finish
        audio_thread.join(timeout=5)
        
        # Close Deepgram connection
        if deepgram_connection:
            try:
                deepgram_connection.finish()
            except Exception as e:
                print(f"Error closing Deepgram connection: {e}")
        
        print("Call session ended")


def main():
    """Main function to start the Flask server"""
    try:
        print(f"Starting server on port {PORT}...")
        app.run(port=PORT, debug=DEBUG, threaded=True)
    except Exception as e:
        print(f"Error starting server: {e}")
    finally:
        call_active.clear()

if __name__ == "__main__":
    main()
