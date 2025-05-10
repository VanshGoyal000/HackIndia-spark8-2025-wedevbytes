# WhatsApp Legal Assistant (JavaScript Implementation)

A Node.js implementation of the WhatsApp bot for the Legal Assistant RAG system.

## Prerequisites

1. Node.js (version 14 or later)
2. npm (Node Package Manager)
3. Twilio account with WhatsApp capability
4. RAG API server running (from the Python implementation)

## Setup Instructions

1. **Install Dependencies**

```bash
cd e:\EstateNet\new\whatsapp_example
npm install
```

2. **Configure Environment Variables**

Update the `.env` file with your credentials:

```
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
RAG_API_URL=http://localhost:8000
```

3. **Start the Server**

```bash
npm start
```

For development with auto-reload:

```bash
npm run dev
```

4. **Expose your Server with ngrok**

```bash
ngrok http 3000
```

Note the HTTPS URL provided by ngrok (e.g., `https://abc123.ngrok.io`).

5. **Configure Twilio Webhook**

- Go to the Twilio Console > WhatsApp Sandbox
- Set the "When a message comes in" webhook to:
  ```
  https://abc123.ngrok.io/whatsapp
  ```
- Set the HTTP method to POST
- Save your changes

## How It Works

1. The WhatsApp bot receives messages from users via Twilio
2. It manages conversation state for each user:
   - Bot selection
   - Question answering
3. It communicates with the RAG API to:
   - Get available bots
   - Query bots with user questions
4. It formats and sends responses back to the user via WhatsApp

## User Commands

- Numbers 1-4: Select a legal domain
- Any text: Ask a legal question (after selecting a domain)
- "menu": Show the domain selection menu
- "help": Show available commands
- "exit": Reset the conversation

## Connecting to the RAG API

This implementation expects the RAG API to be available at the URL specified in the `RAG_API_URL` environment variable. Make sure the API server from the Python implementation is running and accessible.

## Development Notes

- User sessions are stored in memory and will be lost if the server restarts
- For production, use a database to store session information
- WhatsApp messages have a character limit, so long responses are split into multiple messages

## Troubleshooting

If messages are being received by ngrok but the bot is not responding, try these steps:

1. **Check your Twilio webhook configuration**
   - Make sure the webhook URL is set to `https://your-ngrok-url/whatsapp`
   - Verify the HTTP method is set to POST
   - In the Twilio console, check the webhook logs to see if requests are being sent

2. **Run the test script**
   ```bash
   node test.js
   ```
   This will check your environment variables and Twilio connectivity

3. **Check server logs**
   - Look for any error messages in the server console
   - Verify that the server is receiving incoming requests

4. **Debug request details**
   - Send a test message to your WhatsApp number
   - Check the server logs to see the full request details
   - Visit `http://localhost:3000` for health info

5. **Verify RAG API connection**
   - Make sure the RAG API server is running
   - Test the API directly: `curl http://localhost:8000/bots`

6. **Common issues:**
   - TWILIO_PHONE_NUMBER should include the country code (e.g., +1234567890)
   - Webhook URL must be HTTPS (which ngrok provides)
   - Twilio requires proper authorization in webhook requests

## Troubleshooting WhatsApp Response Issues

If the server receives WhatsApp messages but doesn't send responses back, try these specific steps:

### 1. Verify Twilio Sandbox Connection

When using the Twilio Sandbox for WhatsApp, make sure:

- You've joined the sandbox by sending "join <sandbox-code>" to the Twilio WhatsApp number
- Your phone number is properly formatted as international format (e.g., +919528771561)
- Test the direct connection using our test script:
  ```bash
  node twilio-test.js
  ```

### 2. Test Basic Connectivity

Send these special test messages to diagnose issues:

- `test` - Tests basic message response functionality
- `debug api` - Tests connection to the RAG API
- `check bots` - Lists available bots from the RAG API

### 3. Check Server Logs

Look for these key indicators in the logs:

- "Response XML:" - Shows the Twilio response being generated
- Error messages when trying to send responses
- Successful Twilio API responses

### 4. Try Direct Testing Endpoint

Test message sending directly via browser:
```
http://localhost:3000/send-test-message?to=+919528771561
```

### 5. Common Issues with Twilio Sandbox

- **21608 error**: The user needs to message the sandbox first
- **20003/20005 errors**: Authentication issues with Twilio credentials
- **Response format**: Must be properly formatted TwiML
- **Character limits**: WhatsApp messages have length restrictions

### 6. Troubleshooting Button Messages

If you're using WhatsApp buttons or templates:

1. **Button Messages**:
   - Check `Request Body` in logs for `MessageType: "button"` and `ButtonText`
   - Our webhook handler extracts text from both regular and button messages
   - Use the `direct-test.js` script to test template messages:
     ```bash
     node direct-test.js +919528771561
     ```

2. **Testing with cURL**:
   ```bash
   curl 'https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json' \
   -X POST \
   --data-urlencode 'To=whatsapp:+919XXXXXXXX' \
   --data-urlencode 'From=whatsapp:+14155238886' \
   --data-urlencode 'Body=Test message' \
   -u YOUR_ACCOUNT_SID:YOUR_AUTH_TOKEN
   ```

3. **Common Button Message Issues**:
   - Ensure webhook properly extracts `ButtonText` and `ButtonPayload`
   - Different handling may be needed for interactive buttons vs text messages
   - Payload format must match what's expected in your webhook handler
