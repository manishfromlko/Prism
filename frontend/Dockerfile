FROM node:20-alpine

WORKDIR /app

ARG PYTHON_API_URL=http://backend:8000
ENV PYTHON_API_URL=$PYTHON_API_URL

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000
ENV NODE_ENV=production
CMD ["npm", "run", "start"]
