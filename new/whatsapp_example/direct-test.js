require('dotenv').config();
const twilio = require('twilio');

// This script directly tests sending WhatsApp messages through Twilio
// It bypasses your Express app to isolate issues

async function runDirectTest() {
  console.log('🔄 Running Direct Twilio API Test');
  console.log('================================');
  
  // Get environment variables
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken = process.env.TWILIO_AUTH_TOKEN;
  const twilioPhoneNumber = process.env.TWILIO_PHONE_NUMBER;
  
  // Validate environment variables
  if (!accountSid || !authToken || !twilioPhoneNumber) {
    console.error('❌ Missing Twilio credentials in .env file');
    return;
  }
  
  console.log(`Using Twilio account: ${accountSid}`);
  console.log(`Using WhatsApp number: ${twilioPhoneNumber}`);
  
  // Initialize Twilio client
  const client = twilio(accountSid, authToken);
  
  // Get recipient from command line
  const recipientNumber = process.argv[2];
  if (!recipientNumber) {
    console.error('❌ Please provide a recipient number as argument');
    console.log('Usage: node direct-test.js 919528771561');
    return;
  }
  
  // Format recipient for WhatsApp
  const to = `whatsapp:${recipientNumber.startsWith('+') ? recipientNumber : '+' + recipientNumber}`;
  const from = `whatsapp:${twilioPhoneNumber}`;
  
  console.log(`Sending test message to ${to}...`);
  
  try {
    // 1. Check account status first
    console.log('\n🔍 Checking account status...');
    const account = await client.api.accounts(accountSid).fetch();
    console.log(`Account Name: ${account.friendlyName}`);
    console.log(`Account Status: ${account.status}`);
    console.log(`Account Type: ${account.type}`);
    
    // 2. Send a simple text message
    console.log('\n1️⃣ Sending simple text message...');
    const message1 = await client.messages.create({
      body: 'This is a test message from the Legal Assistant WhatsApp bot.',
      from: from,
      to: to
    });
    
    console.log('✅ Message sent!');
    console.log(`SID: ${message1.sid}, Status: ${message1.status}`);
    
    // 3. Send a message with formatting
    console.log('\n2️⃣ Sending formatted message...');
    const message2 = await client.messages.create({
      body: '*Bold text* _Italic text_ ~Strikethrough~ ```Code block```',
      from: from,
      to: to
    });
    
    console.log('✅ Message sent!');
    console.log(`SID: ${message2.sid}, Status: ${message2.status}`);
    
    // 4. Send a welcome message that mimics the app's welcome message
    console.log('\n3️⃣ Sending welcome message with numbered options...');
    const message3 = await client.messages.create({
      body: WELCOME_MESSAGE,
      from: from,
      to: to
    });
    
    console.log('✅ Message sent!');
    console.log(`SID: ${message3.sid}, Status: ${message3.status}`);
    
    console.log('\n✅ Test completed successfully');
    
  } catch (error) {
    console.error('❌ Error sending message:', error.message);
    console.error('Error code:', error.code);
    console.error('Error status:', error.status);
    
    if (error.code === 21608) {
      console.log('\nℹ️ The recipient needs to join your WhatsApp sandbox first');
      console.log(`Ask them to send "join <sandbox-code>" to ${twilioPhoneNumber}`);
      console.log('Find your sandbox code in the Twilio Console > Messaging > Try it out > Send a WhatsApp message');
    }
    
    console.error('\nFull error details:', error);
  }
}

// Use the same welcome message as the main app for consistency in testing
const WELCOME_MESSAGE = `🔍 *Welcome to Legal Assistant!*

Please select a legal domain by replying with the number:

1️⃣ *IPC Bot* (Indian Penal Code)
2️⃣ *RTI Bot* (Right to Information Act)
3️⃣ *Labor Law Bot* (Labor and Employment Laws)
4️⃣ *Constitution Bot* (Constitutional Rights & Articles)

_Example: Send "1" to select IPC Bot_`;

runDirectTest();
