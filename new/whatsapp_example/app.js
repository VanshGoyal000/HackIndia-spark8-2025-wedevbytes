require('dotenv').config();
const express = require('express');
const axios = require('axios');
const twilio = require('twilio');
const bodyParser = require('body-parser');

// Initialize Express app
const app = express();
app.use(bodyParser.urlencoded({ extended: false }));

// Initialize Twilio client
const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

// RAG API URL
const ragApiUrl = process.env.RAG_API_URL || 'http://localhost:8000';

// Add special handling for Twilio sandbox
const isSandboxMode = true; // Set to true while using Twilio sandbox

// Add a test message for debugging
const TEST_MESSAGE = "This is a test response from the Legal Assistant WhatsApp bot. If you can see this message, the connection is working correctly!";

// Available bots
const LEGAL_BOTS = {
  '1': 'IPC Bot',
  '2': 'RTI Bot',
  '3': 'Labor Law Bot',
  '4': 'Constitution Bot'
};

// User sessions (in-memory for simplicity, use a database in production)
const userSessions = {};

// Define welcome message
const WELCOME_MESSAGE = `🔍 *Welcome to Legal Assistant!*

Please select a legal domain by replying with the number:

1️⃣ *IPC Bot* (Indian Penal Code)
2️⃣ *RTI Bot* (Right to Information Act)
3️⃣ *Labor Law Bot* (Labor and Employment Laws)
4️⃣ *Constitution Bot* (Constitutional Rights & Articles)

_Example: Send "1" to select IPC Bot_`;

// Define help message
const HELP_MESSAGE = `🔎 *Legal Assistant Commands*

- Send a *number (1-4)* to select a legal domain
- Type your *legal question* after selecting a domain
- Type *"menu"* to see the domain selection options again
- Type *"help"* to see this help message
- Type *"exit"* to reset the conversation`;

// Enhance logging middleware to see full request details and handle message types better
app.use((req, res, next) => {
  console.log('------------------------------');
  console.log('Incoming Request at:', new Date().toISOString());
  console.log('Request URL:', req.originalUrl);
  console.log('Request Method:', req.method);
  console.log('Request Headers:', JSON.stringify(req.headers, null, 2));
  console.log('Request Body:', JSON.stringify(req.body, null, 2));
  console.log('Request Query:', JSON.stringify(req.query, null, 2));
  console.log('------------------------------');
  next();
});

// Add a stripped-down endpoint for basic response testing
app.post('/whatsapp-basic-test', (req, res) => {
  console.log('Basic test received:', req.body);
  
  const twiml = new twilio.twiml.MessagingResponse();
  twiml.message('This is a basic test response from the WhatsApp bot.');
  
  // Send the response directly
  res.set('Content-Type', 'text/xml');
  res.send(twiml.toString());
});

// Add additional debugging middleware specifically for the WhatsApp endpoint
app.use('/whatsapp', (req, res, next) => {
  console.log('🔍 WHATSAPP WEBHOOK RECEIVED:');
  console.log('Time:', new Date().toISOString());
  console.log('From:', req.body.From);
  console.log('Message:', req.body.Body);
  console.log('Message Type:', req.body.MessageType);
  console.log('Full request body:', JSON.stringify(req.body, null, 2));
  
  // Track this incoming request for monitoring
  const requestId = Date.now().toString();
  console.log(`Request ID: ${requestId}`);
  req.requestId = requestId;
  
  next();
});

// Create a proper response logger
const logResponse = (res, twiml, requestId) => {
  const responseXml = twiml.toString();
  console.log(`📤 SENDING RESPONSE for request ${requestId}:`);
  console.log('Response XML:', responseXml);
  
  // Override the original send method to log when it's actually sent
  const originalSend = res.send;
  res.send = function(body) {
    console.log(`✅ Response ${requestId} sent successfully with status ${res.statusCode}`);
    return originalSend.call(this, body);
  };
  
  return res.type('text/xml').send(responseXml);
};

// Create a shared function for handling WhatsApp messages
async function handleWhatsAppMessage(req, res, requestId) {
  try {
    // Enhanced message extraction to handle both regular text and button messages
    const incomingMsg = req.body.Body?.trim() || req.body.ButtonText?.trim() || '';
    const buttonPayload = req.body.ButtonPayload || null; 
    const sender = req.body.From; // Format: 'whatsapp:+1234567890'
    const to = req.body.To; // The number the message was sent to
    const messageType = req.body.MessageType || 'text'; // Could be 'text', 'button', etc.
    
    console.log(`📩 Message details [${requestId}]:`);
    console.log(`- Type: ${messageType}`);
    console.log(`- From: ${sender}`);
    console.log(`- To: ${to}`);
    console.log(`- Message: ${incomingMsg}`);
    if (buttonPayload) {
      console.log(`- Button payload: ${buttonPayload}`);
    }
    
    // Create Twilio response object
    const twiml = new twilio.twiml.MessagingResponse();
    
    // Handle 'hello' or initial messages
    if (incomingMsg?.toLowerCase() === 'hello' || 
        incomingMsg?.toLowerCase() === 'hi' ||
        incomingMsg?.toLowerCase() === 'hlo' || 
        !userSessions[sender]) {
      
      // Create or reset session
      userSessions[sender] = { 
        selectedBot: null, 
        stage: 'selecting_bot',
        lastInteraction: Date.now()
      };
      
      console.log(`🤖 [${requestId}] Creating new session and sending welcome message`);
      twiml.message(WELCOME_MESSAGE);
      return logResponse(res, twiml, requestId);
    }

    // For debugging - send an immediate test response
    if (incomingMsg?.toLowerCase() === 'test') {
      console.log(`🧪 [${requestId}] Sending test message`);
      twiml.message(TEST_MESSAGE);
      return logResponse(res, twiml, requestId);
    }

    // Handle special case for Twilio sandbox join command
    if (incomingMsg?.toLowerCase().includes('join') && isSandboxMode) {
      console.log(`🔄 [${requestId}] Processing sandbox join command`);
      twiml.message("Welcome to the Legal Assistant! You've successfully joined the WhatsApp sandbox. " + 
                  "Type 'menu' to see available options or 'test' to verify connection.");
      return logResponse(res, twiml, requestId);
    }
    
    // Validate the incoming message
    if (!incomingMsg) {
      console.warn(`⚠️ [${requestId}] Received empty message`);
      twiml.message("I couldn't understand your message. Please try again or type 'help' for assistance.");
      return logResponse(res, twiml, requestId);
    }
    
    // Special debug command to test RAG API connectivity
    if (incomingMsg?.toLowerCase() === 'debug api') {
      console.log(`🔌 [${requestId}] Testing RAG API connection`);
      try {
        await axios.get(ragApiUrl + '/health');
        twiml.message("✅ Successfully connected to RAG API");
      } catch (error) {
        console.error(`❌ [${requestId}] RAG API connection failed:`, error.message);
        twiml.message(`❌ Failed to connect to RAG API at ${ragApiUrl}: ${error.message}`);
      }
      return logResponse(res, twiml, requestId);
    }
    
    // Initialize or retrieve user session
    if (!userSessions[sender]) {
      console.log(`🔄 [${requestId}] Creating missing session for existing user`);
      userSessions[sender] = { 
        selectedBot: null, 
        stage: 'selecting_bot',
        lastInteraction: Date.now()
      };
      twiml.message(WELCOME_MESSAGE);
      return logResponse(res, twiml, requestId);
    }
    
    // Get the current session
    const session = userSessions[sender];
    console.log(`💡 [${requestId}] Current session state:`, JSON.stringify(session));
    
    // Check for special commands
    if (incomingMsg.toLowerCase() === 'help') {
      console.log(`❓ [${requestId}] Processing help command`);
      twiml.message(HELP_MESSAGE);
      return logResponse(res, twiml, requestId);
    }
    
    if (incomingMsg?.toLowerCase() === 'menu') {
      console.log(`📋 [${requestId}] Processing menu command`);
      session.selectedBot = null;
      session.stage = 'selecting_bot';
      twiml.message(WELCOME_MESSAGE);
      return logResponse(res, twiml, requestId);
    }
    
    if (incomingMsg?.toLowerCase() === 'exit') {
      console.log(`🚪 [${requestId}] Processing exit command`);
      if (userSessions[sender]) {
        delete userSessions[sender];
      }
      twiml.message("Conversation reset. Type 'menu' to start again.");
      return logResponse(res, twiml, requestId);
    }
    
    // Special command to check available bots
    if (incomingMsg?.toLowerCase() === 'check bots') {
      console.log(`🤖 [${requestId}] Checking available bots`);
      try {
        const availableBots = await getAvailableBots();
        twiml.message(`Available bots: ${availableBots.join(', ')}`);
      } catch (error) {
        console.error(`❌ [${requestId}] Error getting bots:`, error.message);
        twiml.message(`❌ Failed to get available bots: ${error.message}`);
      }
      return logResponse(res, twiml, requestId);
    }
    
    // Check if the message is a bot selection (1-4) regardless of current state
    if (/^[1-4]$/.test(incomingMsg)) {
      console.log(`🔄 [${requestId}] Detected bot selection number: ${incomingMsg}`);
      
      // If user already had a bot selected, inform them about switching
      let switchingMessage = "";
      if (session.selectedBot && session.stage === 'asking_question') {
        const previousBot = session.selectedBot;
        switchingMessage = `You were previously using ${previousBot}. Switching to `;
        console.log(`🔀 [${requestId}] User is switching from ${previousBot}`);
      }
      
      const botName = LEGAL_BOTS[incomingMsg];
      console.log(`🎯 [${requestId}] User selected bot: ${botName}`);
      
      try {
        // Check if the bot is available
        const availableBots = await getAvailableBots();
        console.log(`📋 [${requestId}] Available bots:`, availableBots);
        
        if (availableBots.includes(botName)) {
          console.log(`✅ [${requestId}] Bot ${botName} is available, updating session`);
          session.selectedBot = botName;
          session.stage = 'asking_question';
          
          twiml.message(
            `✅ ${switchingMessage}*${botName}*\n\nPlease ask your legal question and I'll provide an answer based on relevant legal documents.`
          );
        } else {
          console.log(`❌ [${requestId}] Bot ${botName} is not available`);
          twiml.message(`❌ Sorry, ${botName} is not available. Please select another option.`);
        }
      } catch (error) {
        console.error(`❌ [${requestId}] Error checking available bots:`, error);
        twiml.message('❌ Sorry, I encountered an error checking available bots. Please try again.');
      }
      
      return logResponse(res, twiml, requestId);
    }
    
    // Handle bot selection stage (if not a number 1-4)
    if (session.stage === 'selecting_bot') {
      console.log(`❓ [${requestId}] Invalid bot selection: ${incomingMsg}`);
      twiml.message(`Please select a legal domain by replying with a number from 1-4:\n\n${WELCOME_MESSAGE}`);
      return logResponse(res, twiml, requestId);
    }
    
    // Handle legal questions
    if (session.stage === 'asking_question') {
      console.log(`❓ [${requestId}] Processing legal question for bot ${session.selectedBot}: ${incomingMsg}`);
      try {
        const botName = session.selectedBot;
        
        // Query the RAG API
        console.log(`🔍 [${requestId}] Querying bot ${botName}`);
        const result = await queryBot(botName, incomingMsg);
        
        if (result) {
          console.log(`✅ [${requestId}] Got answer from ${botName}`);
          const answer = result.answer;
          
          // Format source citations if available
          let sourceText = '';
          if (result.sources && result.sources.length > 0) {
            const sources = result.sources.slice(0, 2).map((source, i) => 
              `Source ${i + 1}: ${source.source}, Page: ${source.page}`
            );
            
            if (sources.length > 0) {
              sourceText = '\n\n*Sources:*\n' + sources.join('\n');
            }
          }
          
          // Prepare response with emojis for better readability
          const responseText = `🔍 *Question:*\n${incomingMsg}\n\n📝 *Answer:*\n${answer}${sourceText}\n\n_(Ask another question or type 'menu' to change legal domain)_`;
          
          // Log the full response for debugging
          console.log(`📝 [${requestId}] Response text length: ${responseText.length}`);
          
          // Split long messages if needed (WhatsApp has a 1600 character limit)
          if (responseText.length > 1500) {
            console.log(`📏 [${requestId}] Response exceeds limit, splitting into multiple messages`);
            const parts = splitMessageIntoParts(responseText, 1500);
            
            twiml.message(parts[0]);
            
            // Send subsequent parts using the Twilio API directly
            console.log(`📤 [${requestId}] Will send ${parts.length - 1} additional messages after the main response`);
            
            // Use setTimeout to send the additional messages after responding to Twilio
            setTimeout(async () => {
              try {
                for (let i = 1; i < parts.length; i++) {
                  console.log(`📤 [${requestId}] Sending part ${i+1} of ${parts.length}`);
                  await twilioClient.messages.create({
                    body: parts[i],
                    from: `whatsapp:${process.env.TWILIO_PHONE_NUMBER}`,
                    to: sender
                  });
                }
                console.log(`✅ [${requestId}] Successfully sent all ${parts.length} message parts`);
              } catch (err) {
                console.error(`❌ [${requestId}] Error sending additional message parts:`, err);
              }
            }, 500);
          } else {
            console.log(`📝 [${requestId}] Sending single response message`);
            twiml.message(responseText);
          }
        } else {
          console.log(`❌ [${requestId}] No answer from bot ${botName}`);
          twiml.message('❌ Sorry, I could not get an answer from the system. Please try again or type "menu" to restart.');
        }
      } catch (error) {
        console.error(`❌ [${requestId}] Error querying bot:`, error);
        twiml.message('❌ Sorry, I encountered an error while processing your question. Please try again or type "menu" to restart.');
      }
    }
    
    return logResponse(res, twiml, requestId);
  } catch (error) {
    console.error(`❌ [${requestId}] Error handling WhatsApp message:`, error);
    console.error(`❌ [${requestId}] Stack trace:`, error.stack);
    
    // Always send a response, even on error, and log it
    const twiml = new twilio.twiml.MessagingResponse();
    twiml.message('Sorry, we encountered an issue processing your message. Please try again.');
    
    return logResponse(res, twiml, requestId);
  }
}

// WhatsApp webhook - now uses the shared handler function
app.post('/whatsapp', async (req, res) => {
  const requestId = req.requestId || 'unknown';
  console.log(`👉 Processing WhatsApp endpoint request ${requestId}`);
  return handleWhatsAppMessage(req, res, requestId);
});

// Get available bots from the RAG API
async function getAvailableBots() {
  try {
    const response = await axios.get(`${ragApiUrl}/bots`);
    return response.data.filter(bot => bot.available).map(bot => bot.name);
  } catch (error) {
    console.error('Error getting available bots:', error);
    return Object.values(LEGAL_BOTS); // Fallback to all bots if API call fails
  }
}

// Query a bot through the RAG API
async function queryBot(botName, query) {
  try {
    const response = await axios.post(
      `${ragApiUrl}/bots/${encodeURIComponent(botName)}/query`,
      { query }
    );
    
    return {
      answer: response.data.answer,
      sources: response.data.sources.map(source => ({
        source: source.metadata.source.split('/').pop(),
        page: source.metadata.page
      }))
    };
  } catch (error) {
    console.error('Error querying bot:', error);
    return null;
  }
}

// Split a message into multiple parts
function splitMessageIntoParts(message, maxLength) {
  const parts = [];
  for (let i = 0; i < message.length; i += maxLength) {
    parts.push(message.substring(i, i + maxLength));
  }
  return parts;
}

// Health check endpoint
app.get('/', (req, res) => {
  const healthInfo = {
    status: 'running',
    timestamp: new Date().toISOString(),
    twilio: {
      initialized: !!twilioClient,
      accountSid: process.env.TWILIO_ACCOUNT_SID ? `${process.env.TWILIO_ACCOUNT_SID.substring(0, 5)}...` : 'not set',
      phoneNumber: process.env.TWILIO_PHONE_NUMBER || 'not set'
    },
    ragApi: {
      url: ragApiUrl
    },
    activeSessions: Object.keys(userSessions).length
  };
  
  res.json(healthInfo);
});

// Add a new debug endpoint to check if server is receiving webhooks
app.post('/debug-webhook', (req, res) => {
  console.log('Debug webhook received:');
  console.log('Headers:', req.headers);
  console.log('Body:', req.body);
  res.send('Debug webhook received');
});

// Add a direct message sending function for testing
app.get('/send-test-message', async (req, res) => {
  const toNumber = req.query.to; // Format: +1234567890 (without whatsapp: prefix)
  
  if (!toNumber) {
    return res.status(400).json({ error: 'Missing "to" parameter' });
  }
  
  try {
    // Format the number for WhatsApp
    const formattedNumber = `whatsapp:${toNumber}`;
    
    // Send a test message directly
    const message = await twilioClient.messages.create({
      body: 'This is a direct test message from the Legal Assistant WhatsApp bot.',
      from: `whatsapp:${process.env.TWILIO_PHONE_NUMBER}`,
      to: formattedNumber
    });
    
    return res.json({
      success: true,
      messageSid: message.sid,
      status: message.status,
      details: "Message sent successfully"
    });
  } catch (error) {
    console.error('Error sending direct test message:', error);
    return res.status(500).json({
      success: false,
      error: error.message,
      code: error.code,
      details: error.details
    });
  }
});

// Start the server with validations
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
  
  // Validate critical configurations
  if (!process.env.TWILIO_ACCOUNT_SID || !process.env.TWILIO_AUTH_TOKEN || !process.env.TWILIO_PHONE_NUMBER) {
    console.error('⚠️ WARNING: Missing Twilio credentials. WhatsApp functionality may not work correctly.');
  } else {
    console.log('✅ Twilio credentials loaded successfully');
  }
  
  console.log(`🔗 Webhook URL should be configured as: https://your-ngrok-url/whatsapp`);
  console.log(`🔍 For troubleshooting, visit: http://localhost:${PORT}/whatsapp-troubleshoot`);
  console.log(`📱 Test endpoint: https://your-ngrok-url/whatsapp-basic-test`);
});

// Add a simple route to verify Twilio credentials
app.get('/verify-twilio', async (req, res) => {
  try {
    const account = await twilioClient.api.accounts(process.env.TWILIO_ACCOUNT_SID).fetch();
    res.json({
      success: true,
      account_name: account.friendlyName,
      account_status: account.status,
      message: "Twilio credentials are valid"
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      code: error.code,
      message: "Failed to verify Twilio credentials"
    });
  }
});

// Add a WebSocket verification endpoint
app.get('/whatsapp-troubleshoot', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>WhatsApp Troubleshooter</title>
      <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .section { background: #f5f5f5; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        .success { color: green; }
        .error { color: red; }
        button { padding: 8px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
        code { background: #eee; padding: 3px; }
      </style>
    </head>
    <body>
      <h1>WhatsApp Bot Troubleshooter</h1>
      
      <div class="section">
        <h2>1. Twilio Credentials Check</h2>
        <button id="check-creds">Check Credentials</button>
        <div id="creds-result"></div>
      </div>
      
      <div class="section">
        <h2>2. Test Direct Message</h2>
        <p>Phone number: <input type="text" id="phone" placeholder="+919XXXXXXXX" /></p>
        <button id="send-test">Send Test Message</button>
        <div id="message-result"></div>
      </div>
      
      <div class="section">
        <h2>3. Webhook Test</h2>
        <p>Send a test message to your Twilio number and check the server logs.</p>
        <p>Webhook URL should be set to: <code>https://your-ngrok-url/whatsapp</code></p>
      </div>
      
      <script>
        document.getElementById('check-creds').addEventListener('click', async () => {
          const result = document.getElementById('creds-result');
          result.innerHTML = "Checking...";
          
          try {
            const res = await fetch('/verify-twilio');
            const data = await res.json();
            
            if (data.success) {
              result.innerHTML = \`<p class="success">✅ Credentials valid!</p>
                <p>Account: \${data.account_name}</p>
                <p>Status: \${data.account_status}</p>\`;
            } else {
              result.innerHTML = \`<p class="error">❌ Invalid credentials: \${data.message}</p>\`;
            }
          } catch (error) {
            result.innerHTML = \`<p class="error">❌ Error: \${error.message}</p>\`;
          }
        });
        
        document.getElementById('send-test').addEventListener('click', async () => {
          const result = document.getElementById('message-result');
          const phone = document.getElementById('phone').value;
          
          if (!phone) {
            result.innerHTML = '<p class="error">Please enter a phone number</p>';
            return;
          }
          
          result.innerHTML = "Sending...";
          
          try {
            const res = await fetch(\`/send-test-message?to=\${encodeURIComponent(phone)}\`);
            const data = await res.json();
            
            if (data.success) {
              result.innerHTML = \`<p class="success">✅ Message sent!</p>
                <p>SID: \${data.messageSid}</p>
                <p>Status: \${data.status}</p>\`;
            } else {
              result.innerHTML = \`<p class="error">❌ Error: \${data.error}</p>
                <p>Code: \${data.code}</p>\`;
            }
          } catch (error) {
            result.innerHTML = \`<p class="error">❌ Error: \${error.message}</p>\`;
          }
        });
      </script>
    </body>
    </html>
  `);
});

// Add additional debugging middleware for the root path that might receive WhatsApp webhooks
app.use('/', (req, res, next) => {
  if (req.method === 'POST' && req.headers['content-type']?.includes('application/x-www-form-urlencoded') 
      && (req.body.From?.startsWith('whatsapp:') || req.body.MessageSid)) {
    console.log('🔍 WHATSAPP WEBHOOK RECEIVED ON ROOT PATH:');
    console.log('Time:', new Date().toISOString());
    console.log('From:', req.body.From);
    console.log('Message:', req.body.Body);
    console.log('Message Type:', req.body.MessageType);
    console.log('Full request body:', JSON.stringify(req.body, null, 2));
    
    // Track this incoming request for monitoring
    const requestId = Date.now().toString();
    console.log(`Request ID: ${requestId}`);
    req.requestId = requestId;
  }
  next();
});

// Add a POST handler for root path to handle WhatsApp webhooks
app.post('/', async (req, res) => {
  // Check if this is a WhatsApp message from Twilio
  if (req.body.From?.startsWith('whatsapp:') || req.body.MessageSid) {
    console.log('⚠️ WhatsApp webhook received on root path, processing as WhatsApp message');
    
    // Forward to the WhatsApp handler using the shared function
    const requestId = req.requestId || Date.now().toString();
    console.log(`👉 Processing root path WhatsApp request ${requestId}`);
    return handleWhatsAppMessage(req, res, requestId);
  } else {
    // This is not a WhatsApp message, return a simple response
    res.send('Legal Assistant WhatsApp Bot is running. Use POST /whatsapp for WhatsApp webhook.');
  }
});

// Add a direct message sending function
app.get('/direct-message', async (req, res) => {
  const { to, message } = req.query;
  
  if (!to || !message) {
    return res.status(400).json({ error: 'Missing parameters: "to" and "message" are required' });
  }
  
  try {
    // Format the number for WhatsApp if needed
    const formattedNumber = to.startsWith('whatsapp:') ? to : `whatsapp:${to.startsWith('+') ? to : '+' + to}`;
    
    // Send the message
    const sentMessage = await twilioClient.messages.create({
      body: message,
      from: `whatsapp:${process.env.TWILIO_PHONE_NUMBER}`,
      to: formattedNumber
    });
    
    return res.json({
      success: true,
      messageSid: sentMessage.sid,
      status: sentMessage.status,
      details: "Message sent successfully"
    });
  } catch (error) {
    console.error('Error sending direct message:', error);
    return res.status(500).json({
      success: false,
      error: error.message,
      code: error.code,
      details: error.details
    });
  }
});

// Helper function to send a direct message
async function sendWhatsAppMessage(to, message) {
  try {
    // Format the number for WhatsApp if needed
    const formattedNumber = to.startsWith('whatsapp:') ? to : `whatsapp:${to.startsWith('+') ? to : '+' + to}`;
    
    // Send the message
    const sentMessage = await twilioClient.messages.create({
      body: message,
      from: `whatsapp:${process.env.TWILIO_PHONE_NUMBER}`,
      to: formattedNumber
    });
    
    console.log(`Message sent to ${to}: ${sentMessage.sid}`);
    return sentMessage;
  } catch (error) {
    console.error(`Error sending message to ${to}:`, error);
    throw error;
  }
}