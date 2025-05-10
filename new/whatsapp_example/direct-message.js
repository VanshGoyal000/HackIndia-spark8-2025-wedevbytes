require('dotenv').config();
const twilio = require('twilio');

// Initialize Twilio client
const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

/**
 * Sends a WhatsApp message directly to a user
 * 
 * Usage:
 * node direct-message.js +919528771561 "Your message here"
 */
async function sendDirectMessage() {
  const [,, recipient, message] = process.argv;
  
  if (!recipient || !message) {
    console.error('❌ Missing arguments');
    console.log('Usage: node direct-message.js +919528771561 "Your message here"');
    return;
  }
  
  console.log(`Sending message to ${recipient}:`);
  console.log(message);
  
  try {
    // Format the recipient for WhatsApp
    const to = `whatsapp:${recipient.startsWith('+') ? recipient : '+' + recipient}`;
    const from = `whatsapp:${process.env.TWILIO_PHONE_NUMBER}`;
    
    // Send the message
    const sent = await twilioClient.messages.create({
      body: message,
      from: from,
      to: to
    });
    
    console.log(`✅ Message sent successfully!`);
    console.log(`Message SID: ${sent.sid}`);
    console.log(`Status: ${sent.status}`);
  } catch (error) {
    console.error(`❌ Error sending message:`, error);
    
    if (error.code === 21608) {
      console.log('\nℹ️ The recipient needs to join your WhatsApp sandbox first');
      console.log(`Ask them to send "join <sandbox-code>" to ${process.env.TWILIO_PHONE_NUMBER}`);
    }
  }
}

sendDirectMessage();
