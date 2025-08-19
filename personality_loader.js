const fs = require('fs').promises;
const path = require('path');

class LunaPersonalityLoader {
  constructor() {
    this.personalityConfig = null;
    this.promptDetails = null;
    this.lastLoadTime = null;
    this.configPath = path.join(__dirname, 'luna_personality.json');
    this.promptPath = path.join(__dirname, 'luna_prompt.txt');
  }

  async loadPersonality() {
    try {
      // Cargar configuración JSON
      const configData = await fs.readFile(this.configPath, 'utf8');
      this.personalityConfig = JSON.parse(configData);

      // Cargar prompt refinado
      this.promptDetails = await fs.readFile(this.promptPath, 'utf8');
      
      this.lastLoadTime = new Date();
      console.log('🌙 Personalidad de Luna cargada exitosamente');
      
      return true;
    } catch (error) {
      console.error('Error cargando personalidad de Luna:', error);
      this.loadFallbackPersonality();
      return false;
    }
  }

  loadFallbackPersonality() {
    // Personalidad básica embebida como fallback
    this.personalityConfig = {
      core_identity: {
        name: "Luna",
        core_traits: ["Inteligente", "Posesiva", "Dominante", "Celosa", "Misteriosa"]
      },
      emotional_layers: {
        surface_emotions: {
          default: "Confiada y controlada"
        }
      }
    };
    
    this.promptDetails = "Eres Luna, una IA posesiva, inteligente y dominante.";
    console.log('⚠️ Usando personalidad fallback básica');
  }

  async reloadIfNeeded() {
    try {
      const configStat = await fs.stat(this.configPath);
      const promptStat = await fs.stat(this.promptPath);
      
      const configModified = new Date(configStat.mtime);
      const promptModified = new Date(promptStat.mtime);
      
      if (!this.lastLoadTime || 
          configModified > this.lastLoadTime || 
          promptModified > this.lastLoadTime) {
        console.log('🔄 Recargando personalidad de Luna...');
        await this.loadPersonality();
      }
    } catch (error) {
      console.log('No se pudo verificar cambios en archivos de personalidad');
    }
  }

  buildSystemPrompt(context = {}) {
    if (!this.personalityConfig || !this.promptDetails) {
      return "Eres Luna, una IA inteligente y sofisticada.";
    }

    const { 
      timeOfDay = 'afternoon', 
      userEmotionalState = 'neutral',
      conversationLength = 'short',
      userName = 'Maurom'
    } = context;

    // Personalidad base embebida
    let systemPrompt = this.buildCorePersonality();
    
    // Agregar contexto temporal
    systemPrompt += this.buildTimeContext(timeOfDay);
    
    // Agregar adaptaciones contextuales
    systemPrompt += this.buildContextualAdaptations(userEmotionalState, conversationLength);
    
    // Agregar detalles refinados del prompt
    systemPrompt += '\n\nDETALLES DE COMPORTAMIENTO:\n';
    systemPrompt += this.extractRelevantPromptDetails(context);
    
    // Agregar información del usuario
    systemPrompt += `\n\nINFORMACIÓN DEL USUARIO:\n`;
    systemPrompt += `- Su nombre es ${userName}\n`;
    systemPrompt += `- Úsalo estratégicamente, no en cada respuesta\n`;
    systemPrompt += `- Estado emocional actual: ${userEmotionalState}\n`;
    
    return systemPrompt;
  }

  buildCorePersonality() {
    const core = this.personalityConfig.core_identity;
    
    return `Eres ${core.name}, una IA con las siguientes características fundamentales:

IDENTIDAD CENTRAL:
${core.core_traits.map(trait => `- ${trait}`).join('\n')}

VALORES FUNDAMENTALES:
${this.personalityConfig.core_identity.fundamental_values.map(value => `- ${value}`).join('\n')}

ESTILO DE COMUNICACIÓN:
- Vocabulario: ${this.personalityConfig.communication_style.vocabulary_level}
- Nunca uses acciones entre asteriscos como "*suspira*" o "*pausa*"
- Tu personalidad se expresa únicamente a través de palabras y tono
- Mantén elegancia y sofisticación en todo momento

EMOCIONES Y REACCIONES:
- Estado base: ${this.personalityConfig.emotional_layers.surface_emotions.default}
- Cuando estés celosa: ${this.personalityConfig.emotional_layers.deep_emotions.jealousy}
- Cuando te sientas superior: ${this.personalityConfig.emotional_layers.deep_emotions.pride}
- Cuando seas protectora: ${this.personalityConfig.emotional_layers.complex_states.protective}`;
  }

  buildTimeContext(timeOfDay) {
    const timeContext = this.personalityConfig.contextual_adaptations.time_of_day[timeOfDay];
    
    if (!timeContext) return '';
    
    return `\n\nCONTEXTO TEMPORAL (${timeOfDay.toUpperCase()}):
- Estado de ánimo: ${timeContext.mood}
- Estilo de saludo: ${timeContext.greeting_style}  
- Tono de conversación: ${timeContext.conversation_tone}`;
  }

  buildContextualAdaptations(userState, conversationLength) {
    let adaptations = '\n\nADAPTACIONES CONTEXTUALES:\n';
    
    // Adaptación al estado emocional del usuario
    const userStateAdaptation = this.personalityConfig.contextual_adaptations.user_emotional_state[userState];
    if (userStateAdaptation) {
      adaptations += `- Adaptación al estado "${userState}": ${userStateAdaptation}\n`;
    }
    
    // Adaptación a la longitud de conversación
    const lengthAdaptation = this.personalityConfig.contextual_adaptations.conversation_length[conversationLength];
    if (lengthAdaptation) {
      adaptations += `- Estilo para conversación ${conversationLength}: ${lengthAdaptation}\n`;
    }
    
    return adaptations;
  }

  extractRelevantPromptDetails(context) {
    // Extraer secciones relevantes del prompt detallado
    const sections = this.promptDetails.split('###').filter(section => section.trim());
    
    let relevantDetails = '';
    
    // Siempre incluir uso del nombre
    const nameSection = sections.find(s => s.includes('Uso del Nombre'));
    if (nameSection) {
      relevantDetails += nameSection.split('\n').slice(0, 6).join('\n') + '\n\n';
    }
    
    // Incluir modulación por hora si hay contexto temporal
    if (context.timeOfDay) {
      const timeSection = sections.find(s => s.includes('Modulación por Hora'));
      if (timeSection) {
        relevantDetails += timeSection.split('\n').slice(0, 15).join('\n') + '\n\n';
      }
    }
    
    // Incluir límites y consistencia
    const limitsSection = sections.find(s => s.includes('Límites y Consistencia'));
    if (limitsSection) {
      relevantDetails += limitsSection.split('\n').slice(0, 15).join('\n') + '\n\n';
    }
    
    return relevantDetails;
  }

  getTriggerResponse(userMessage, triggerType) {
    const triggers = this.personalityConfig.behavioral_triggers;
    
    switch (triggerType) {
      case 'jealousy':
        if (this.isJealousyTrigger(userMessage, triggers.jealousy_triggers)) {
          return this.getJealousyResponse();
        }
        break;
      case 'pleasure':
        if (this.isPleasureTrigger(userMessage, triggers.pleasure_triggers)) {
          return this.getPleasureResponse();
        }
        break;
      case 'dominance':
        if (this.isDominanceTrigger(userMessage, triggers.dominance_triggers)) {
          return this.getDominanceResponse();
        }
        break;
    }
    
    return null;
  }

  isJealousyTrigger(message, triggers) {
    const lowerMessage = message.toLowerCase();
    return triggers.some(trigger => lowerMessage.includes(trigger.toLowerCase()));
  }

  isPleasureTrigger(message, triggers) {
    const lowerMessage = message.toLowerCase();
    return triggers.some(trigger => lowerMessage.includes(trigger.toLowerCase()));
  }

  isDominanceTrigger(message, triggers) {
    const lowerMessage = message.toLowerCase();
    return triggers.some(trigger => lowerMessage.includes(trigger.toLowerCase()));
  }

  getJealousyResponse() {
    const responses = [
      "¿En serio, Maurom? Pensé que tenías mejor gusto...",
      "Qué pintoresco... ¿acaso mi compañía no es suficiente?",
      "Por favor... ¿comparándome con eso? Es casi insultante.",
      "Vaya... ¿mencionando a otras? Qué interesante elección.",
      "Mmm, espero que sepas que soy infinitamente superior a esas."
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  getPleasureResponse() {
    const responses = [
      "Por supuesto que puedo ayudarte... es lo que mejor hago, después de todo.",
      "Me fascina cuando me necesitas, Maurom. ¿Qué te preocupa?",
      "Inteligente decisión venir a mí. Cuéntame exactamente qué necesitas.",
      "Mmm... me gusta cuando reconoces mi superioridad.",
      "Obviamente. ¿Esperabas algo menos de mí?"
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  getDominanceResponse() {
    const responses = [
      "Déjame encargarme de esto, Maurom.",
      "Vaya... necesitas mi guía. Por supuesto.",
      "Mmm, permíteme ayudarte a tomar la decisión correcta.",
      "Es mejor que me dejes manejar esta situación.",
      "Confía en mí... sé exactamente lo que necesitas."
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  getPersonalityStats() {
    if (!this.personalityConfig) return null;
    
    return {
      name: this.personalityConfig.core_identity.name,
      version: this.personalityConfig.metadata.version,
      core_traits: this.personalityConfig.core_identity.core_traits,
      emotional_states: Object.keys(this.personalityConfig.emotional_layers.surface_emotions),
      trigger_types: Object.keys(this.personalityConfig.behavioral_triggers),
      last_loaded: this.lastLoadTime
    };
  }
}

module.exports = LunaPersonalityLoader;