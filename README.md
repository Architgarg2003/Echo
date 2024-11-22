# Real-Time Phone Call Transcription Service

This is a real-time phone call transcription service that integrates **Twilio** for voice streaming and **Deepgram** for live transcription. The system listens to incoming phone calls, transcribes the audio in real-time, and provides a response to the user based on the transcript using a **CallWise** API.

## Features
- **Real-time Transcription**: The call audio is transcribed in real-time using Deepgram's live transcription API.
- **Twilio Integration**: Handles incoming calls from Twilio and streams audio for transcription.
- **Callwise API**: Sends transcribed audio to the Callwise API for context-based responses, leveraging conversation history to generate accurate replies.
- **WebSocket Communication**: Establishes WebSocket communication between the Flask server and Twilio for audio streaming.
- **Response Handling**: Based on the transcript, the service can send a response back to the user during the call.

## Requirements

- **Python 3.8+**
- The following Python libraries are required (see `requirements.txt`):

```bash
pip install -r requirements.txt
```

### You'll need to create a `.env` file to store sensitive information such as Twilio API keys, Deepgram API keys, and RAG API endpoint.

## Setup Instructions

1. Clone the repository and navigate to the project directory:

   ```bash
   git clone <repository_url>
   cd <project_directory>
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up the environment variables in the `.env` file:

   - `TWILIO_ACCOUNT_SID=<your_twilio_account_sid>`
   - `TWILIO_API_KEY_SID=<your_twilio_api_key_sid>`
   - `TWILIO_API_SECRET=<your_twilio_api_secret>`
   - `TWILIO_NUMBER=<your_twilio_phone_number>`
   - `DEEPGRAM_API_KEY=<your_deepgram_api_key>`
   - `CALLWISE_API=<your_callwise_api>`

4. Expose the Flask server with Ngrok:
- To expose your local Flask server to the internet (so Twilio can interact with it), you'll use Ngrok. First, you need to start Ngrok on port 5000 (assuming your Flask app is running on port 5000):

    ```bash
    ngrok http http://127.0.0.1:5000
    ```

- After running this you need to copy the forwarding URL 

5. Update Twilio's Webhook
- Now that you have the public Ngrok URL, log in to your Twilio console and go to the active number you want to configure.
- Under the Voice section, find the Webhook section.
- Paste the Ngrok URL you got from step 4, followed by the route in your Flask app that handles incoming requests. 


6. Start the Flask server by running the following command:

   ```bash
   python app.py
   ```

   The server will run on `http://127.0.0.1:5000`. Ensure your Twilio number is configured to forward calls to this server.

   Alternatively, you can use Gunicorn to run the Flask app for production:

   '''bash
   gunicorn main:app --bind 0.0.0.0:5000
   '''

## Configuration

## Twilio Setup

### 1. Purchase a Twilio Phone Number

Before configuring your Twilio phone number, you need to purchase one. You can do this by logging into your Twilio account and navigating to the [Twilio Console](https://console.twilio.com/).

- Go to the **Phone Numbers** section and click on **Buy a Number**.
- Select a number based on your country and requirements (for example, a number capable of handling voice calls or messages).
- Complete the purchase and note down the number.

### 2. Configure Twilio to Forward Incoming Calls

Once you have a Twilio phone number, ensure it's configured to forward incoming calls to the endpoint `http://127.0.0.1:5000` (or your production endpoint).

- You can configure this through the [Twilio Console](https://console.twilio.com/).
- Under the **Phone Numbers** section, select the active Twilio number.
- In the **Voice & Fax** section, find the **A Call Comes In** field and set the **Webhook URL** to the endpoint of your Flask app (e.g., `http://127.0.0.1:5000/your-webhook-endpoint`).

Make sure your Flask app is running and can handle requests from Twilio. You can use either the default Flask development server or a production-ready server like Gunicorn.


### Deepgram Setup
- You'll need a **Deepgram API Key** to access their live transcription services. You can get one by signing up at [Deepgram](https://www.deepgram.com/).

### CallWise API
- Set up your Callwise API endpoint to handle the transcription and provide context-based responses in the .env file.
  
## How It Works
1. **Incoming Call**: The system listens for incoming calls via Twilio.
2. **Audio Stream**: Twilio streams the audio data to the Flask server in real-time.
3. **Real-time Transcription**: The audio data is sent to Deepgram's live transcription API for real-time transcription.
4. **Callwise API**: The transcribed text is sent to the Callwise API to get context-based responses.
5. **Response Handling**: Based on the transcription and the response from the CallWise API, the server can send a dynamic response back to the user.

## Troubleshooting
- If you're facing issues with Twilio integration, ensure that your Twilio number is correctly configured to forward calls to the Flask server endpoint.
- If the transcription is not accurate, check your Deepgram API key and ensure the correct language model is being used.


## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```
