const fetch = require('node-fetch');

// Configuración
const APP_URL = process.env.RAILWAY_STATIC_URL || process.env.APP_URL || 'http://localhost:3000';
const PING_INTERVAL = 14 * 60 * 1000; // 14 minutos
const MAX_RETRIES = 3;

class KeepAlive {
  constructor() {
    this.retryCount = 0;
    this.isRunning = false;
  }

  async ping() {
    try {
      console.log(`🏓 Ping a ${APP_URL}/api/ping - ${new Date().toISOString()}`);
      
      const response = await fetch(`${APP_URL}/api/ping`, {
        method: 'GET',
        timeout: 10000,
        headers: {
          'User-Agent': 'KeepAlive-Bot/1.0'
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`✅ Pong recibido - Uptime: ${Math.floor(data.uptime)}s`);
        this.retryCount = 0;
        return true;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      this.retryCount++;
      console.error(`❌ Error en ping (intento ${this.retryCount}/${MAX_RETRIES}):`, error.message);
      
      if (this.retryCount >= MAX_RETRIES) {
        console.log('🔄 Máximo de reintentos alcanzado, esperando al siguiente ciclo...');
        this.retryCount = 0;
      }
      return false;
    }
  }

  start() {
    if (this.isRunning) {
      console.log('⚠️ KeepAlive ya está corriendo');
      return;
    }

    this.isRunning = true;
    console.log(`🚀 KeepAlive iniciado - Ping cada ${PING_INTERVAL / 1000 / 60} minutos`);
    console.log(`🎯 Target URL: ${APP_URL}`);

    // Ping inmediato
    this.ping();

    // Programar pings periódicos
    this.intervalId = setInterval(() => {
      this.ping();
    }, PING_INTERVAL);

    // Manejar señales de terminación
    process.on('SIGINT', () => this.stop());
    process.on('SIGTERM', () => this.stop());
  }

  stop() {
    if (!this.isRunning) return;

    console.log('🛑 Deteniendo KeepAlive...');
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    this.isRunning = false;
    process.exit(0);
  }
}

// Auto-start en producción
if (process.env.NODE_ENV === 'production') {
  const keepAlive = new KeepAlive();
  
  // Esperar 30 segundos antes del primer ping para que el servidor arranque
  setTimeout(() => {
    keepAlive.start();
  }, 30000);
}

module.exports = KeepAlive;