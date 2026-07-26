# Development image — hot reload via the bind mount in docker-compose.yml.
# Not used in production; see frontend.Dockerfile for that image.

FROM node:22-alpine
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
EXPOSE 3000
CMD ["npm", "run", "dev"]
