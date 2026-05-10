# Stage 1 - build
#   Installs Node via fnm, then compiles native addons (canvas, sharp).
#   python3 is only needed here by node-gyp.
FROM debian:bookworm-slim AS build

ARG NODE_VERSION=v20.19.1
ARG FNM_VERSION=1.37.1

ENV DEBIAN_FRONTEND=noninteractive \
    FNM_DIR=/opt/fnm \
    PATH=/opt/fnm:$PATH

# Native build deps for canvas + sharp, plus python3 for node-gyp
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    unzip \
    build-essential \
    python3 \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    libwebp-dev \
    libvips-dev \
    && rm -rf /var/lib/apt/lists/*

# Install node via fnm
RUN curl -fsSL https://fnm.vercel.app/install | bash -s -- \
      --install-dir "$FNM_DIR" \
      --skip-shell && \
    fnm install "${NODE_VERSION}" && \
    fnm default "${NODE_VERSION}"

# Expose the installed node directly; note that the fnm binary is not needed at runtime
ENV PATH=/opt/fnm/node-versions/${NODE_VERSION}/installation/bin:$PATH

WORKDIR /app
COPY package.json ./

RUN npm install --omit=dev && \
    npm rebuild canvas --build-from-source

# Stage 2 - runtime
#   Only runtime shared libs; so no compilers, utilities, no python, no dev tools.
#   TBH we could spend more time making this image smaller but it's super tedious.
FROM debian:bookworm-slim AS runtime

ARG NODE_VERSION=v20.19.1

ENV NODE_OPTIONS="--max-old-space-size=512" \
    PATH=/opt/node/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libjpeg62-turbo \
    libgif7 \
    librsvg2-2 \
    libwebp7 \
    libvips42 \
    && rm -rf /var/lib/apt/lists/*

# Copy only the Node installation over from the 'build' stage (so not fnm binary, aliases, or other versions)
COPY --from=build /opt/fnm/node-versions/${NODE_VERSION}/installation /opt/node

WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY generate.js ./

RUN useradd -m qruser
USER qruser

ENTRYPOINT ["node", "/app/generate.js"]
