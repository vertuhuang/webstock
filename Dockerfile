FROM node:22-alpine

RUN apk add tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo Asia/Shanghai > /etc/timezone && \
    apk del tzdata

WORKDIR /app

COPY package*.json ./

RUN npm config set registry https://mirrors.cloud.tencent.com/npm/ && \
    npm install --production --ignore-scripts && \
    npm cache clean --force

COPY server.js ./
COPY stock-database.json ./
COPY hk-stock-database.json ./
COPY stock-monitor.html ./
COPY stock-monitor-tdesign.html ./
COPY public/ ./public/

ENV NODE_ENV=production
ENV PORT=80

EXPOSE 80

CMD ["node", "server.js"]
