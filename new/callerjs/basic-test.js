require('dotenv').config();
const express = require('express');
const app = express();
const PORT = 3010;

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Log all requests
app.use((req, res, next) => {
  console.log(`Request received: ${req.method} ${req.path}`);
  console.log('Query:', req.query);
  console.log('Body:', req.body);
  next();
});

// Basic test endpoint
app.all('/', (req, res) => {
  const response = `<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="female">Hello World</Say><Hangup/></Response>`;
  res.set('Content-Type', 'text/xml');
  res.send(response);
});

app.listen(PORT, () => {
  console.log(`Basic test server running on port ${PORT}`);
});
