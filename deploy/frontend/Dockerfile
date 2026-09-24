FROM node:22-alpine AS build
WORKDIR /workspace
COPY docs/business/design-system docs/business/design-system
COPY frontend/package.json frontend/package-lock.json* frontend/
WORKDIR /workspace/frontend
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY deploy/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/frontend/dist /usr/share/nginx/html/app
EXPOSE 80
