require('dotenv').config();
const express = require('express');
const axios = require('axios');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const app = express();
const PORT = process.env.PORT || 3009;

// Initialize Google Gemini API
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });

// Configure RAG API (your existing API with the legal bots)
const RAG_API_URL = process.env.RAG_API_URL || 'http://localhost:8000';

// Track call sessions
const callSessions = {};

// Available legal bots with enhanced descriptions
const LEGAL_BOTS = {
  '1': {
    name: 'RTI Bot',
    shortDesc: 'Right to Information',
    response: 'For Right to Information Act requests, you need to file an application with a fee of 10 rupees. Public authorities must respond within 30 days. You can appeal if denied information within 30 days to the first appellate authority.'
  },
  '2': {
    name: 'IPC Bot',
    shortDesc: 'Indian Penal Code',
    response: 'Under Indian Penal Code Section 420, cheating is punishable with imprisonment up to 7 years and a fine. For other sections like 302 for murder or 376 for rape, punishments vary accordingly.'
  },
  '3': {
    name: 'Labor Law Bot',
    shortDesc: 'Labor Laws',
    response: 'For labor disputes, approach your local labor commissioner first. Employees are entitled to minimum wages, overtime pay, and safe working conditions as per the labor laws.'
  },
  '4': {
    name: 'Constitution Bot',
    shortDesc: 'Constitutional Rights',
    response: 'Article 32 of the Constitution provides right to constitutional remedies. This fundamental right allows citizens to approach the Supreme Court directly for enforcement of their rights.'
  },
  '5': {
    name: 'Family Law Bot',
    shortDesc: 'Family & Marriage Laws',
    response: 'Family law covers marriage, divorce, adoption, and child custody. For divorce, different personal laws have different waiting periods and grounds depending on your religion.'
  }
};

// Parse form data (Exotel sends form-urlencoded data)
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Log incoming requests with more detail
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  console.log('Request query:', req.query);
  if (Object.keys(req.body).length > 0) {
    console.log('Request body:', req.body);
  }
  
  // Add response logging
  const originalSend = res.send;
  res.send = function(body) {
    console.log('Response sent:', body);
    return originalSend.call(this, body);
  };
  
  next();
});

// Set BASE_URL for callbacks - make sure to use a direct URL without dynamic components
const getBaseUrl = (req) => {
  return process.env.BASE_URL || `${req.protocol}://${req.get('host')}`;
};

// ROOT ENDPOINT - Modified to use Play tag for audio URLs instead of Say tag
app.get('/', (req, res) => {
  try {
    // Extract Exotel call parameters
    const callSid = req.query.CallSid || 'unknown';
    const callerNumber = req.query.CallFrom || req.query.From || '0000000000';
    
    console.log(`New call from ${callerNumber}, CallSid: ${callSid}`);
    
    // Initialize session for this call
    callSessions[callSid] = {
      callerNumber,
      stage: 'bot-selection',  // Skip greeting since Exotel already did it
      language: 'en',
      selectedBot: null,
      lastQuery: null,
      lastResponse: null,
      timestamp: new Date().toISOString()
    };
    
    // Using Play tag with audio URLs instead of Say tag
    const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/menu-options.mp3</Play>
<Gather action="${getBaseUrl(req)}/bot-selection" numDigits="1"/>
</Response>`;
    
    console.log('Sending domain selection options with audio');
    res.set('Content-Type', 'text/xml');
    return res.send(exotelResponse);
  } catch (error) {
    console.error('Error in root handler:', error);
    const errorResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/error.mp3</Play>
<Hangup/>
</Response>`;
    res.set('Content-Type', 'text/xml');
    return res.send(errorResponse);
  }
});

// Handle both GET and POST for bot selection with simplified XML response
app.all('/bot-selection', (req, res) => {
  try {
    // Get parameters from either query or body
    const params = {...req.query, ...req.body};
    console.log('Bot selection - Full params:', params);
    
    const callSid = params.CallSid || params.callsid || 'unknown';
    const digits = params.digits || params.Digits || '';
    
    console.log(`Bot selection - CallSid: ${callSid}, Selected: ${digits}`);
    
    // Get or create session
    if (!callSessions[callSid]) {
      console.log(`Creating new session for call ${callSid}`);
      callSessions[callSid] = {
        callerNumber: params.CallFrom || params.From || 'unknown',
        stage: 'bot-selection',
        language: 'en',
        timestamp: new Date().toISOString()
      };
    }
    
    // Update session with bot selection
    const session = callSessions[callSid];
    session.stage = 'bot-selected';
    
    if (LEGAL_BOTS[digits]) {
      botName = LEGAL_BOTS[digits].name;
      console.log(`Selected bot: ${botName} for call ${callSid}`);
      
      // Store the selected bot
      session.selectedBot = LEGAL_BOTS[digits].name;
      
      // Now prompt to record a question instead of just playing an audio response
      const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/please-ask-question.mp3</Play>
<Record action="${getBaseUrl(req)}/process-recording" maxLength="30" finishOnKey="#" playBeep="true"/>
</Response>`;
      
      res.set('Content-Type', 'text/xml');
      return res.send(exotelResponse);
    } else {
      console.log(`Invalid selection: ${digits} for call ${callSid}`);
      
      // Invalid selection response
      const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/invalid-selection.mp3</Play>
<Gather action="${getBaseUrl(req)}/bot-selection" numDigits="1"/>
</Response>`;
      
      res.set('Content-Type', 'text/xml');
      return res.send(exotelResponse);
    }
  } catch (error) {
    console.error('Error in bot selection:', error);
    const errorResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/error.mp3</Play>
<Hangup/>
</Response>`;
    res.set('Content-Type', 'text/xml');
    return res.send(errorResponse);
  }
});

// NEW ENDPOINT: Process recording and convert speech to text
app.all('/process-recording', async (req, res) => {
  try {
    const params = {...req.query, ...req.body};
    
    const callSid = params.CallSid || params.callsid || 'unknown';
    const recordingUrl = params.RecordingUrl || '';
    const recordingDuration = params.RecordingDuration || '0';
    
    console.log(`Processing recording for call ${callSid}`);
    console.log(`Recording URL: ${recordingUrl}`);
    console.log(`Recording Duration: ${recordingDuration} seconds`);
    
    if (!callSessions[callSid]) {
      console.log(`No session found for call ${callSid}`);
      const errorResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/error.mp3</Play>
<Hangup/>
</Response>`;
      res.set('Content-Type', 'text/xml');
      return res.send(errorResponse);
    }
    
    const session = callSessions[callSid];
    
    // Check if we have a recording URL and valid bot selection
    if (!recordingUrl || !session.selectedBot) {
      console.log('Missing recording URL or no bot selected');
      const errorResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/error.mp3</Play>
<Play>${process.env.AUDIO_BASE_URL}/prompt-after-answer.mp3</Play>
<Gather action="${getBaseUrl(req)}/after-answer" numDigits="1"/>
</Response>`;
      res.set('Content-Type', 'text/xml');
      return res.send(errorResponse);
    }
    
    // Process recording - convert speech to text
    let transcriptionText = '';
    let botResponse = '';
    
    try {
      // Option 1: Use your existing RAG API's speech-to-text endpoint
      console.log('Sending recording to speech-to-text service...');
      const transcriptionResponse = await axios.post(`${RAG_API_URL}/speech-to-text`, {
        audio_url: recordingUrl,
        language: session.language || 'english'
      }, { timeout: 15000 });
      
      transcriptionText = transcriptionResponse.data.text || '';
      console.log(`Transcription result: "${transcriptionText}"`);
      
      // Store the transcription in the session
      session.lastQuery = transcriptionText;
      
      // If we have text, query the bot with it
      if (transcriptionText) {
        console.log(`Querying bot "${session.selectedBot}" with: "${transcriptionText}"`);
        const botQueryResponse = await axios.post(`${RAG_API_URL}/bots/${encodeURIComponent(session.selectedBot)}/query`, {
          query: transcriptionText
        }, { timeout: 15000 });
        
        botResponse = botQueryResponse.data.answer || '';
        console.log(`Bot response: "${botResponse}"`);
        
        // Store the bot response in session
        session.lastResponse = botResponse;
      } else {
        console.log('Transcription resulted in empty text');
        botResponse = "I couldn't understand your question. Please try again.";
      }
    } catch (error) {
      console.error('Error processing speech to text:', error);
      botResponse = "Sorry, I encountered an error processing your question.";
    }
    
    // Now we need to convert the text response to audio
    // Since we're working with pre-recorded audio files, we'll fall back to a generic response
    // In a real system, you'd use a TTS service to generate audio from botResponse
    
    let responsePath = `${process.env.AUDIO_BASE_URL}/generic-response.mp3`;
    
    // For now, just use the bot number to select a pre-recorded response
    const botNumber = Object.keys(LEGAL_BOTS).find(key => LEGAL_BOTS[key].name === session.selectedBot);
    if (botNumber) {
      responsePath = `${process.env.AUDIO_BASE_URL}/bot-${botNumber}-response.mp3`;
    }
    
    const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${responsePath}</Play>
<Play>${process.env.AUDIO_BASE_URL}/prompt-after-answer.mp3</Play>
<Gather action="${getBaseUrl(req)}/after-answer" numDigits="1"/>
</Response>`;
    
    res.set('Content-Type', 'text/xml');
    return res.send(exotelResponse);
  } catch (error) {
    console.error('Error in process-recording:', error);
    const errorResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/error.mp3</Play>
<Hangup/>
</Response>`;
    res.set('Content-Type', 'text/xml');
    return res.send(errorResponse);
  }
});

// After answer endpoint - updated to use audio
app.all('/after-answer', (req, res) => {
  try {
    const params = {...req.query, ...req.body};
    const callSid = params.CallSid || params.callsid || 'unknown';
    const digits = params.digits || params.Digits || '';
    
    console.log(`After answer - CallSid: ${callSid}, Choice: ${digits}`);
    
    if (digits === '1') {
      // Another question - go back to bot selection
      const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/select-another-domain.mp3</Play>
<Gather action="${getBaseUrl(req)}/bot-selection" numDigits="1"/>
</Response>`;
      res.set('Content-Type', 'text/xml');
      return res.send(exotelResponse);
    } else {
      // End call
      console.log(`Ending call ${callSid}`);
      delete callSessions[callSid];
      const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/goodbye.mp3</Play>
<Hangup/>
</Response>`;
      res.set('Content-Type', 'text/xml');
      return res.send(exotelResponse);
    }
  } catch (error) {
    console.error('Error in after-answer:', error);
    const errorResponse = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>${process.env.AUDIO_BASE_URL}/thank-you.mp3</Play>
<Hangup/>
</Response>`;
    res.set('Content-Type', 'text/xml');
    return res.send(errorResponse);
  }
});

// Add debug test endpoint with minimal XML
app.get('/test-exotel', (req, res) => {
  const exotelResponse = `<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="female">Test response</Say><Hangup/></Response>`;
  res.set('Content-Type', 'text/xml');
  return res.send(exotelResponse);
});

// Healthcheck endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    activeCalls: Object.keys(callSessions).length,
    timestamp: new Date().toISOString()
  });
});

// Debug endpoint to view active sessions
app.get('/debug/sessions', (req, res) => {
  res.json({
    sessionCount: Object.keys(callSessions).length,
    sessions: callSessions
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Exotel IVR server running on http://localhost:${PORT}`);
  console.log(`Make sure Exotel Passthru applet is configured to call: https://your-ngrok-url/`);
  console.log('Current active sessions:', Object.keys(callSessions).length);
});
