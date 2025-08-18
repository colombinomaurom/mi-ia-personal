const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static('public'));

// Configuración de la IA
const AI_CONFIG = {
  name: "MiIA Personal",
  personality: "Asistente personal inteligente y útil",
  capabilities: [
    "responder preguntas",
    "ayudar con tareas",
    "dar consejos",
    "resolver problemas",
    "conversar naturalmente"
  ]
};

// Base de conocimiento expandible
let knowledgeBase = {
  saludos: [
    "¡Hola! Soy tu IA personal. ¿En qué puedo ayudarte?",
    "¡Hey! ¿Qué necesitas hoy?",
    "¡Saludos! Estoy aquí para ayudarte.",
  ],
  despedidas: [
    "¡Hasta la vista! Fue un placer ayudarte.",
    "¡Nos vemos! Siempre estaré aquí cuando me necesites.",
    "¡Chau! Que tengas un excelente día.",
  ],
  conversacion: {
    "cómo estás": "¡Estoy funcionando perfectamente! ¿Y tú cómo andás?",
    "qué puedes hacer": `Puedo ayudarte con muchas cosas: ${AI_CONFIG.capabilities.join(', ')}. ¿Qué necesitas?`,
    "quién eres": `Soy ${AI_CONFIG.name}, tu ${AI_CONFIG.personality}`,
  }
};

// Historial de conversaciones (en memoria, se resetea al reiniciar)
let conversationHistory = [];

// Funciones de procesamiento de texto
function normalizeText(text) {
  return text.toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function calculateSimilarity(text1, text2) {
  const words1 = text1.split(' ');
  const words2 = text2.split(' ');
  const intersection = words1.filter(word => words2.includes(word));
  const union = [...new Set([...words1, ...words2])];
  return intersection.length / union.length;
}

function findBestMatch(input, options) {
  let bestMatch = { text: '', similarity: 0 };
  
  for (const option of options) {
    const similarity = calculateSimilarity(
      normalizeText(input), 
      normalizeText(option)
    );
    
    if (similarity > bestMatch.similarity) {
      bestMatch = { text: option, similarity };
    }
  }
  
  return bestMatch;
}

// Funciones de análisis de sentimientos básico
function analyzeSentiment(text) {
  const positiveWords = ['bien', 'bueno', 'excelente', 'genial', 'perfecto', 'gracias', 'feliz'];
  const negativeWords = ['mal', 'malo', 'terrible', 'horrible', 'problema', 'error', 'triste'];
  
  const normalizedText = normalizeText(text);
  let score = 0;
  
  positiveWords.forEach(word => {
    if (normalizedText.includes(word)) score++;
  });
  
  negativeWords.forEach(word => {
    if (normalizedText.includes(word)) score--;
  });
  
  if (score > 0) return 'positivo';
  if (score < 0) return 'negativo';
  return 'neutral';
}

// Motor de respuestas inteligente
function generateResponse(userInput, userId = 'default') {
  const normalizedInput = normalizeText(userInput);
  
  // Detectar saludos
  const greetings = ['hola', 'hey', 'saludos', 'buenos dias', 'buenas tardes', 'buenas noches'];
  if (greetings.some(greeting => normalizedInput.includes(greeting))) {
    return knowledgeBase.saludos[Math.floor(Math.random() * knowledgeBase.saludos.length)];
  }
  
  // Detectar despedidas
  const farewells = ['chau', 'adios', 'hasta luego', 'nos vemos', 'bye'];
  if (farewells.some(farewell => normalizedInput.includes(farewell))) {
    return knowledgeBase.despedidas[Math.floor(Math.random() * knowledgeBase.despedidas.length)];
  }
  
  // Buscar en conocimiento específico
  for (const [key, value] of Object.entries(knowledgeBase.conversacion)) {
    if (normalizedInput.includes(normalizeText(key))) {
      return value;
    }
  }
  
  // Análisis de sentimiento para respuestas empáticas
  const sentiment = analyzeSentiment(userInput);
  
  // Respuestas contextuales basadas en patrones
  if (normalizedInput.includes('ayuda') || normalizedInput.includes('problema')) {
    return "Claro, estaré encantado de ayudarte. ¿Podrías contarme más detalles sobre lo que necesitas?";
  }
  
  if (normalizedInput.includes('tiempo') || normalizedInput.includes('hora')) {
    return `Son las ${new Date().toLocaleTimeString('es-ES')} del ${new Date().toLocaleDateString('es-ES')}.`;
  }
  
  if (normalizedInput.includes('fecha') || normalizedInput.includes('dia')) {
    return `Hoy es ${new Date().toLocaleDateString('es-ES', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })}.`;
  }
  
  // Respuestas por sentimiento
  if (sentiment === 'positivo') {
    return "¡Me alegra saber que estás bien! ¿Hay algo específico en lo que pueda ayudarte?";
  } else if (sentiment === 'negativo') {
    return "Entiendo que puede ser frustrante. Estoy aquí para ayudarte. ¿Qué está pasando?";
  }
  
  // Respuesta por defecto inteligente
  const responses = [
    "Esa es una pregunta interesante. ¿Podrías darme más contexto?",
    "Entiendo lo que me dices. ¿Hay algo específico en lo que te pueda ayudar?",
    "Hmm, déjame pensar en eso. ¿Podrías explicarme un poco más?",
    "Es un tema fascinante. ¿Qué aspecto te interesa más?",
    "Me parece importante lo que mencionas. ¿Cómo puedo asistirte mejor?"
  ];
  
  return responses[Math.floor(Math.random() * responses.length)];
}

// Rutas de la API
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    name: AI_CONFIG.name,
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    capabilities: AI_CONFIG.capabilities
  });
});

app.post('/api/chat', (req, res) => {
  try {
    const { message, userId = 'default' } = req.body;
    
    if (!message || typeof message !== 'string') {
      return res.status(400).json({ 
        error: 'Mensaje requerido', 
        response: 'Por favor envía un mensaje válido.' 
      });
    }
    
    // Agregar al historial
    const timestamp = new Date().toISOString();
    conversationHistory.push({
      userId,
      message,
      timestamp,
      type: 'user'
    });
    
    // Generar respuesta
    const response = generateResponse(message, userId);
    
    // Agregar respuesta al historial
    conversationHistory.push({
      userId,
      message: response,
      timestamp: new Date().toISOString(),
      type: 'ai'
    });
    
    // Mantener solo los últimos 1000 mensajes para no sobrecargar memoria
    if (conversationHistory.length > 1000) {
      conversationHistory = conversationHistory.slice(-1000);
    }
    
    res.json({
      response,
      timestamp,
      userId,
      conversationId: `${userId}_${Date.now()}`
    });
    
  } catch (error) {
    console.error('Error en chat:', error);
    res.status(500).json({ 
      error: 'Error interno', 
      response: 'Lo siento, hubo un problema. ¿Podrías intentar de nuevo?' 
    });
  }
});

app.get('/api/history/:userId?', (req, res) => {
  const { userId = 'default' } = req.params;
  const { limit = 50 } = req.query;
  
  const userHistory = conversationHistory
    .filter(msg => msg.userId === userId)
    .slice(-parseInt(limit));
    
  res.json({
    history: userHistory,
    count: userHistory.length,
    userId
  });
});

app.post('/api/learn', (req, res) => {
  try {
    const { pattern, response, category = 'conversacion' } = req.body;
    
    if (!pattern || !response) {
      return res.status(400).json({ 
        error: 'Pattern y response son requeridos' 
      });
    }
    
    if (!knowledgeBase[category]) {
      knowledgeBase[category] = {};
    }
    
    knowledgeBase[category][pattern.toLowerCase()] = response;
    
    res.json({ 
      success: true, 
      message: 'Conocimiento agregado exitosamente',
      pattern,
      response,
      category
    });
    
  } catch (error) {
    console.error('Error en aprendizaje:', error);
    res.status(500).json({ error: 'Error al agregar conocimiento' });
  }
});

app.get('/api/knowledge', (req, res) => {
  res.json({
    knowledgeBase,
    totalEntries: Object.keys(knowledgeBase.conversacion || {}).length,
    categories: Object.keys(knowledgeBase)
  });
});

// Ruta para mantener vivo el servicio (anti-sleep para Railway)
app.get('/api/ping', (req, res) => {
  res.json({ 
    pong: true, 
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Manejo de errores global
app.use((error, req, res, next) => {
  console.error('Error global:', error);
  res.status(500).json({ 
    error: 'Error interno del servidor',
    response: 'Lo siento, algo salió mal. Por favor intenta de nuevo.'
  });
});

// Manejo de rutas no encontradas
app.use('*', (req, res) => {
  res.status(404).json({ 
    error: 'Ruta no encontrada',
    availableRoutes: ['/api/chat', '/api/status', '/api/history', '/api/learn', '/api/knowledge']
  });
});

// Keep-alive para Railway (evita que se duerma)
if (process.env.NODE_ENV === 'production') {
  setInterval(() => {
    fetch(`http://localhost:${PORT}/api/ping`)
      .catch(err => console.log('Keep-alive ping:', err.message));
  }, 14 * 60 * 1000); // Cada 14 minutos
}

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`🤖 ${AI_CONFIG.name} corriendo en puerto ${PORT}`);
  console.log(`📱 Acceso web: http://localhost:${PORT}`);
  console.log(`🚀 API lista en: http://localhost:${PORT}/api/`);
});

module.exports = app;