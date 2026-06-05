FROM node:22-alpine

WORKDIR /app

COPY package.json package.json
COPY tsconfig.json tsconfig.json
COPY vite.config.ts vite.config.ts
COPY index.html index.html
RUN npm install

COPY src ./src

EXPOSE 5173
CMD ["npm", "run", "dev"]
