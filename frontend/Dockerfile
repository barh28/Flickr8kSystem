# Multi-stage: build the static bundle with Node, then serve it with nginx.
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
# Prefer a reproducible install from the lock file. npm's lock file does not
# always record the optional, platform-specific native deps (e.g. rollup/oxlint
# binaries, @emnapi/*) for every OS/CPU, so `npm ci` can fail on a machine whose
# architecture differs from where the lock was generated. Fall back to a plain
# install in that case so the image builds on any computer (amd64 or arm64).
RUN npm ci || (echo "npm ci failed (lock not in sync for this platform); falling back to npm install" && npm install)

COPY . .

# Baked into the bundle at build time. This is the BROWSER-facing gateway URL
# (the published host port), not the docker-internal address.
ARG VITE_API_BASE_URL=http://localhost:8080
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
