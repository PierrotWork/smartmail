# ============================================
# Multi-stage Dockerfile для фронта
# ============================================
#
# Собирается двумя способами:
#   docker build --target dev  .    # для локальной разработки (Vite dev-server)
#   docker build --target prod .    # для продакшена (nginx + статика)
#
# В docker-compose файлах указывается нужный target.
# ============================================


# ---------- Development ----------
FROM node:20-alpine AS dev
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


# ---------- Build ----------
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

# В build-time подставляем URL API (задаётся в docker-compose.prod.yml через build args)
ARG VITE_API_BASE_URL=/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build


# ---------- Production ----------
FROM nginx:1.25-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
