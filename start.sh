#!/bin/bash

# 股票监控系统 - 快速启动脚本

echo "🚀 股票监控系统 - 启动中..."

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 错误：未检测到Node.js，请先安装Node.js (https://nodejs.org/)"
    exit 1
fi

echo "✅ Node.js版本：$(node -v)"

# 检查依赖是否安装
if [ ! -d "node_modules" ]; then
    echo "📦 首次运行，正在安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请检查网络连接或手动运行 npm install"
        exit 1
    fi
    echo "✅ 依赖安装完成"
else
    echo "✅ 依赖已安装"
fi

# 创建public目录（如果不存在）
if [ ! -d "public" ]; then
    mkdir public
    echo "📁 创建public目录"
fi

# 将前端页面复制到public目录
if [ ! -f "public/stock-monitor.html" ]; then
    cp stock-monitor.html public/
    echo "📄 复制前端页面到public目录"
fi

# 启动服务器
echo ""
echo "🌐 正在启动后端服务器..."
SERVER_PORT="${PORT:-3000}"
SERVER_HOST="${HOST:-127.0.0.1}"
SERVER_URL="http://${SERVER_HOST}:${SERVER_PORT}"
echo "📡 服务地址：${SERVER_URL}"
echo "📖 API健康检查：${SERVER_URL}/api/health"
echo ""
echo "💡 使用提示："
echo "   1. 服务器启动后，在浏览器访问 ${SERVER_URL}"
echo "   2. 在页面中添加股票代码（如 sh600519, hk00700）"
echo "   3. 数据将每3秒自动更新"
echo ""
echo "⚠️  注意：请确保端口${SERVER_PORT}未被占用"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

node server.js
