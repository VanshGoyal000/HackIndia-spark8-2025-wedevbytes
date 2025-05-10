require('dotenv').config();
const express = require('express');
const axios = require('axios');
const app = express();
const port = 3009;

// RAG API URL - this should be your API running at port 8000
const RAG_API_URL = process.env.RAG_API_URL || 'http://localhost:8000';

// Call sessions to track state
const callSessions = {};

// Parse form data sent by Exotel (application/x-www-form-urlencoded)
app.use(express.urlencoded({ extended: true }));

// Log incoming requests
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  console.log('Request body:', req.body);
  next();
});

// Initial welcome endpoint
app.post('/hello', (req, res) => {
  const callSid = req.body.CallSid;
  const callerNumber = req.body.From;
  
  console.log(`New call from ${callerNumber}, CallSid: ${callSid}`);
  
  // Initialize session for this call
  callSessions[callSid] = {
    callerNumber,
    stage: 'welcome',
    language: 'en',
    botType: null
  };
  
  const xml = `
    <Response>
      <Say voice="female" language="en">Welcome to the Legal Assistant. Please select your preferred language.</Say>
      <Say voice="female" language="en">Press 1 for English. Press 2 for Hindi.</Say>
      <GetDigits timeout="5" numDigits="1" callbackUrl="/select-language" />
    </Response>
  `;
  res.type('text/xml');
  res.send(xml);
});

// Language selection handler
app.post('/select-language', (req, res) => {
  const callSid = req.body.CallSid;
  const digits = req.body.digits || '1'; // Default to English if no selection
  
  // Get or create session
  if (!callSessions[callSid]) {
    callSessions[callSid] = {
      callerNumber: req.body.From,
      stage: 'language-selected'
    };
  }
  
  // Update session with language selection
  const session = callSessions[callSid];
  session.language = digits === '1' ? 'en' : 'hi';
  session.stage = 'language-selected';
  
  // Language-specific prompts
  const langPrompt = session.language === 'en' 
    ? 'You selected English. Now, please select a legal domain.'
    : 'आपने हिंदी चुनी है। अब, कृपया एक कानूनी क्षेत्र चुनें।';
    
  const menuPrompt = session.language === 'en'
    ? 'Press 1 for RTI information. Press 2 for IPC information. Press 3 for labor laws. Press 4 for constitutional rights.'
    : 'आरटीआई जानकारी के लिए 1 दबाएं। आईपीसी जानकारी के लिए 2 दबाएं। श्रम कानूनों के लिए 3 दबाएं। संवैधानिक अधिकारों के लिए 4 दबाएं।';
  
  const xml = `
    <Response>
      <Say voice="female" language="${session.language}">${langPrompt}</Say>
      <Say voice="female" language="${session.language}">${menuPrompt}</Say>
      <GetDigits timeout="5" numDigits="1" callbackUrl="/select-domain" />
    </Response>
  `;
  
  res.type('text/xml');
  res.send(xml);
});

// Domain selection handler
app.post('/select-domain', (req, res) => {
  const callSid = req.body.CallSid;
  const digits = req.body.digits;
  
  if (!callSessions[callSid]) {
    // If session is lost, restart
    return res.redirect(307, '/hello');
  }
  
  const session = callSessions[callSid];
  session.stage = 'domain-selected';
  
  // Map digits to bot types
  const botTypes = {
    '1': 'RTI Bot',
    '2': 'IPC Bot',
    '3': 'Labor Law Bot',
    '4': 'Constitution Bot'
  };
  
  session.botType = botTypes[digits] || 'RTI Bot';
  
  // Language-specific prompts
  const selectedPrompt = session.language === 'en'
    ? `You selected ${session.botType}. Please ask your question after the beep.`
    : `आपने ${session.botType} चुना है। कृपया बीप के बाद अपना प्रश्न पूछें।`;
  
  const xml = `
    <Response>
      <Say voice="female" language="${session.language}">${selectedPrompt}</Say>
      <Record maxLength="30" playBeep="true" callbackUrl="/process-question" />
    </Response>
  `;
  
  res.type('text/xml');
  res.send(xml);
});

// Process recorded question
app.post('/process-question', async (req, res) => {
  const callSid = req.body.CallSid;
  const recordingUrl = req.body.RecordingUrl;
  const recordingStatus = req.body.RecordingStatus;
  
  console.log(`Recording status: ${recordingStatus}, URL: ${recordingUrl}`);
  
  if (!callSessions[callSid] || recordingStatus !== 'completed' || !recordingUrl) {
    const xml = `
      <Response>
        <Say voice="female" language="en">Sorry, we couldn't record your question. Please try again later.</Say>
        <Hangup />
      </Response>
    `;
    return res.type('text/xml').send(xml);
  }
  
  const session = callSessions[callSid];
  
  try {
    // 1. Convert speech to text
    const transcriptionResponse = await axios.post(`${RAG_API_URL}/speech-to-text`, {
      audio_url: recordingUrl,
      language: session.language === 'en' ? 'english' : 'hindi'
    });
    
    const questionText = transcriptionResponse.data.text;
    console.log(`Transcribed question: ${questionText}`);
    
    // 2. Query RAG API with the question
    const ragResponse = await axios.post(`${RAG_API_URL}/bots/${encodeURIComponent(session.botType)}/query`, {
      query: questionText
    });
    
    const answerText = ragResponse.data.answer;
    console.log(`Answer: ${answerText}`);
    
    // 3. Convert answer to speech
    const ttsResponse = await axios.post(`${RAG_API_URL}/text-to-speech`, {
      text: answerText,
      language: session.language === 'en' ? 'english' : 'hindi'
    });
    
    const audioFile = ttsResponse.data.audio_file;
    
    // 4. Play the answer to the user
    const followupPrompt = session.language === 'en'
      ? 'Press 1 to ask another question. Press 2 to end the call.'
      : 'एक और सवाल पूछने के लिए 1 दबाएं। कॉल समाप्त करने के लिए 2 दबाएं।';
    
    const xml = `
      <Response>
        <Play>${RAG_API_URL}/audio/${audioFile}</Play>
        <Say voice="female" language="${session.language}">${followupPrompt}</Say>
        <GetDigits timeout="5" numDigits="1" callbackUrl="/after-answer" />
      </Response>
    `;
    
    res.type('text/xml').send(xml);
  } catch (error) {
    console.error('Error processing question:', error);
    
    const errorPrompt = session.language === 'en'
      ? 'Sorry, we encountered an error processing your question. Please try again later.'
      : 'क्षमा करें, आपके प्रश्न को संसाधित करने में एक त्रुटि हुई है। कृपया बाद में पुन: प्रयास करें।';
    
    const xml = `
      <Response>
        <Say voice="female" language="${session.language}">${errorPrompt}</Say>
        <Hangup />
      </Response>
    `;
    
    res.type('text/xml').send(xml);
  }
});

// Handle user's choice after hearing the answer
app.post('/after-answer', (req, res) => {
  const callSid = req.body.CallSid;
  const digits = req.body.digits;
  
  if (!callSessions[callSid]) {
    // If session is lost, restart
    return res.redirect(307, '/hello');
  }
  
  const session = callSessions[callSid];
  
  if (digits === '1') {
    // User wants to ask another question
    const askAgainPrompt = session.language === 'en'
      ? 'Please ask your next question after the beep.'
      : 'कृपया बीप के बाद अपना अगला प्रश्न पूछें।';
    
    const xml = `
      <Response>
        <Say voice="female" language="${session.language}">${askAgainPrompt}</Say>
        <Record maxLength="30" playBeep="true" callbackUrl="/process-question" />
      </Response>
    `;
    
    return res.type('text/xml').send(xml);
  }
  
  // Default: end call
  const goodbyePrompt = session.language === 'en'
    ? 'Thank you for calling our Legal Assistant. Goodbye!'
    : 'हमारे लीगल असिस्टेंट को कॉल करने के लिए धन्यवाद। अलविदा!';
  
  const xml = `
    <Response>
      <Say voice="female" language="${session.language}">${goodbyePrompt}</Say>
      <Hangup />
    </Response>
  `;
  
  // Clean up the session
  delete callSessions[callSid];
  
  res.type('text/xml').send(xml);
});

// Status update endpoint for call monitoring
app.post('/call-status', (req, res) => {
  const callSid = req.body.CallSid;
  const callStatus = req.body.CallStatus;
  
  console.log(`Call ${callSid} status: ${callStatus}`);
  
  // If call ended, clean up session
  if (callStatus === 'completed' || callStatus === 'failed' || callStatus === 'busy' || callStatus === 'no-answer') {
    delete callSessions[callSid];
  }
  
  res.sendStatus(200);
});

// Health check endpoint
app.get('/health', async (req, res) => {
  try {
    // Check if RAG API is accessible
    await axios.get(`${RAG_API_URL}/health`, { timeout: 2000 });
    
    res.json({
      status: 'healthy',
      activeCalls: Object.keys(callSessions).length
    });
  } catch (error) {
    res.status(500).json({
      status: 'unhealthy',
      error: error.message
    });
  }
});

app.listen(port, () => {
  console.log(`IVR server running on http://localhost:${port}`);
});
