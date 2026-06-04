FROM node:18-alpine
WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json ./

# 安装生产依赖
RUN npm ci --omit=dev --ignore-scripts

# 复制应用代码
COPY server.js ./
COPY stock-database.json ./
COPY stock-monitor.html ./
COPY stock-monitor-tdesign.html ./

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "server.js"]
