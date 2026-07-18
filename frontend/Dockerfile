# Multi-stage: `dev` runs Vite's dev server with HMR; `prod` builds static
# assets and serves them via nginx.
FROM node:20-alpine AS base
WORKDIR /app

# ---- dev ----
FROM base AS dev
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- build ----
FROM base AS build
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# ---- prod ----
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
