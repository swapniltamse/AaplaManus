const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Sample data (replace with database integration in production)
const clients = [
  { id: 1, name: 'John Doe', policies: ['Auto', 'Home'], renewalDate: '2023-08-15' },
  { id: 2, name: 'Jane Smith', policies: ['Life', 'Health'], renewalDate: '2023-09-22' },
];

// Routes
app.get('/api/clients', (req, res) => {
  res.json(clients);
});

app.get('/api/clients/:id', (req, res) => {
  const client = clients.find(c => c.id === parseInt(req.params.id));
  if (!client) return res.status(404).send('Client not found');
  res.json(client);
});

// AI Chat endpoint (placeholder)
app.post('/api/chat', (req, res) => {
  const { message } = req.body;
  // In a real implementation, integrate with an AI service
  res.json({ reply: `AI response to: ${message}` });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});