# Usar Node.js oficial
FROM node:18-alpine

# Crear directorio de trabajo
WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm ci --only=production && npm cache clean --force

# Copiar código fuente
COPY . .

# Crear directorio público si no existe
RUN mkdir -p public

# Exponer puerto
EXPOSE 3000

# Variables de entorno por defecto
ENV NODE_ENV=production
ENV PORT=3000

# Comando de inicio
CMD ["npm", "start"]