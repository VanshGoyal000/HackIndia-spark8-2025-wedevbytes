require('dotenv').config();
const twilio = require('twilio');
const readline = require('readline');

// Initialize Twilio client
const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const twilioPhoneNumber = process.env.TWILIO_PHONE_NUMBER;

// Create readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

async function runTwilioTest() {
  console.log('📱 Twilio WhatsApp Messaging Test Tool');
  console.log('=====================================');
  
  // Verify environment variables
  if (!accountSid || !authToken || !twilioPhoneNumber) {
    console.error('❌ Error: Missing required environment variables');
    console.log('Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env file');
    rl.close();
    return;
  }
  
  console.log(`Using Twilio account: ${accountSid}`);
  console.log(`Using WhatsApp number: ${twilioPhoneNumber}`);
  
  // Initialize Twilio client
  let client;
  try {
    client = twilio(accountSid, authToken);
    console.log('✅ Successfully initialized Twilio client');
  } catch (error) {
    console.error('❌ Error initializing Twilio client:', error);
    rl.close();
    return;
  }
  
  // Get recipient number
  rl.question('Enter recipient WhatsApp number (with country code, e.g., +919528771561): ', async (recipientNumber) => {
    if (!recipientNumber.startsWith('+')) {
      console.log('Adding + prefix to number');
      recipientNumber = '+' + recipientNumber;
    }
    
    console.log(`Sending test message to ${recipientNumber}...`);
    
    try {
      // Send a WhatsApp message
      const message = await client.messages.create({
        body: 'This is a test message from the Legal Assistant WhatsApp bot.',
        from: `whatsapp:${twilioPhoneNumber}`,
        to: `whatsapp:${recipientNumber}`
      });
      
      console.log('✅ Message sent successfully!');
      console.log(`Message SID: ${message.sid}`);
      console.log(`Status: ${message.status}`);
      console.log(`Date Sent: ${message.dateCreated}`);
      
    } catch (error) {
      console.error('❌ Error sending message:', error.message);
      console.error('Error code:', error.code);
      console.error('Error details:', error);
      
      if (error.code === 21608) {
        console.log('\n👉 The recipient may need to send a message to your WhatsApp sandbox first.');
        console.log(`   Ask them to send "join <your-sandbox-code>" to ${twilioPhoneNumber}`);
      }
      
      if (error.code === 20003 || error.code === 20005) {
        console.log('\n👉 Authentication error. Check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.');
      }
      
      // Additional common error codes
      if (error.code === 21211) {
        console.log('\n👉 Invalid phone number format. Make sure to include country code.');
      }
      
      if (error.code === 21606) {
        console.log('\n👉 This WhatsApp number is not enabled for the sandbox.');
      }
      
      if (error.code === 21612) {
        console.log('\n👉 The template has not been approved or does not exist.');
      }
    }
    
    rl.close();
  });
}

runTwilioTest();
