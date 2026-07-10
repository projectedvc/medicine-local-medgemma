FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY tsconfig.json tsconfig.json
COPY vite.config.ts vite.config.ts
COPY index.html index.html
RUN npm ci

COPY src ./src
COPY public ./public

EXPOSE 5173
CMD ["npm", "run", "dev"]
