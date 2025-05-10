require('dotenv').config();
const axios = require('axios');
const twilio = require('twilio');

async function runTests() {
  console.log('Running WhatsApp bot tests...');
  
  // 1. Check environment variables
  console.log('\n--- Environment Variables Check ---');
  const requiredEnvVars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'];
  let envOk = true;
  
  for (const varName of requiredEnvVars) {
    if (!process.env[varName]) {
      console.error(`❌ Missing required environment variable: ${varName}`);
      envOk = false;
    } else {
      console.log(`✅ ${varName} is set`);
    }
  }
  
  if (!envOk) {
    console.error('Please set all required environment variables in the .env file');
    return;
  }
  
  // 2. Test Twilio client initialization
  console.log('\n--- Twilio Client Test ---');
  try {
    const client = twilio(
      process.env.TWILIO_ACCOUNT_SID,
      process.env.TWILIO_AUTH_TOKEN
    );
    
    const account = await client.api.accounts(process.env.TWILIO_ACCOUNT_SID).fetch();
    console.log(`✅ Connected to Twilio account: ${account.friendlyName}`);
  } catch (error) {
    console.error('❌ Failed to initialize Twilio client:', error.message);
    return;
  }
  
  // 3. Test ngrok connectivity
  console.log('\n--- Ngrok Connectivity Test ---');
  
  console.log('Please enter your ngrok URL:');
  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  readline.question('ngrok URL: ', async (ngrokUrl) => {
    try {
      const response = await axios.get(ngrokUrl);
      console.log(`✅ Successfully connected to ngrok URL: ${response.status} ${response.statusText}`);
      
      console.log('\n--- Webhook Configuration Instructions ---');
      console.log(`1. Go to https://console.twilio.com/`);
      console.log(`2. Navigate to Messaging > Try it out > Send a WhatsApp message`);
      console.log(`3. Set the webhook URL to: ${ngrokUrl}/whatsapp`);
      console.log(`4. Ensure the HTTP method is set to POST`);
      
      readline.close();
    } catch (error) {
      console.error(`❌ Failed to connect to ngrok URL: ${error.message}`);
      readline.close();
    }
  });
}

runTests();
