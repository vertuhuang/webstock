const express = require('express');
const cors = require('cors');
const axios = require('axios');
const iconv = require('iconv-lite');
const path = require('path');

const app = express();
const PORT = 3000;
const HOST = '127.0.0.1';

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

// ========= 缓存层 =========
const cache = {
    data: null,           // 缓存的股票数据
    timestamp: 0,         // 缓存时间戳
    ttl: 3000,           // 缓存TTL：3秒
    updating: false        // 是否正在更新
};

// 后台定时任务：每3秒更新缓存
let backgroundTask = null;

function startBackgroundTask() {
    if (backgroundTask) return;
    
    backgroundTask = setInterval(async () => {
        if (cache.updating) return;
        
        cache.updating = true;
        try {
            // 如果没有监控的股票，跳过
            if (!cache.lastCodes || cache.lastCodes.length === 0) {
                cache.updating = false;
                return;
            }
            
            const stocks = await fetchStockDataFromAPI(cache.lastCodes);
            cache.data = stocks;
            cache.timestamp = Date.now();
            
            // 推送给所有SSE客户端
            broadcastToSSEClients(stocks);
            
            console.log(`[Background] Cache updated, ${stocks.length} stocks`);
        } catch (error) {
            console.error('[Background] Update failed:', error.message);
        } finally {
            cache.updating = false;
        }
    }, 3000);
    
    console.log('[Background] Task started');
}

// 停止后台任务
function stopBackgroundTask() {
    if (backgroundTask) {
        clearInterval(backgroundTask);
        backgroundTask = null;
        console.log('[Background] Task stopped');
    }
}

// ========= SSE客户端管理 =========
const sseClients = new Set();

function addSSEClient(res) {
    sseClients.add(res);
    console.log(`[SSE] Client connected, total: ${sseClients.size}`);
    
    // 立即发送当前缓存数据
    if (cache.data && cache.data.length > 0) {
        const data = JSON.stringify({ success: true, data: cache.data });
        res.write(`data: ${data}\n\n`);
    }
}

function removeSSEClient(res) {
    sseClients.delete(res);
    console.log(`[SSE] Client disconnected, total: ${sseClients.size}`);
    
    // 如果没有SSE客户端了，停止后台任务
    if (sseClients.size === 0) {
        stopBackgroundTask();
    }
}

function broadcastToSSEClients(stocks) {
    const data = JSON.stringify({ success: true, data: stocks });
    const message = `data: ${data}\n\n`;
    
    sseClients.forEach(client => {
        try {
            client.write(message);
        } catch (error) {
            console.error('[SSE] Broadcast error:', error.message);
        }
    });
    
    console.log(`[SSE] Broadcasted to ${sseClients.size} clients`);
}

// ========= API调用函数 =========
async function fetchStockDataFromAPI(codes) {
    const codesStr = codes.join(',');
    const url = 'http://qt.gtimg.cn/q=' + codesStr;
    
    const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 10000
    });
    
    const data = iconv.decode(response.data, 'gbk');
    return parseStockData(data, codes);
}

// 获取缓存的股票数据（如果缓存过期则调用API）
async function getCachedStocks(codes) {
    const now = Date.now();
    
    // 检查缓存是否有效
    if (cache.data && (now - cache.timestamp) < cache.ttl) {
        console.log(`[Cache] Hit, age: ${now - cache.timestamp}ms`);
        return cache.data;
    }
    
    // 缓存过期或不存在，调用API
    console.log(`[Cache] Miss, fetching from API`);
    const stocks = await fetchStockDataFromAPI(codes);
    
    // 更新缓存
    cache.data = stocks;
    cache.timestamp = now;
    cache.lastCodes = codes;
    
    return stocks;
}

// ========= 搜索股票API（代理新浪财经搜索）=========
async function searchStocksFromAPI(keyword) {
    // 新浪财经搜索API
    const url = 'https://suggest3.sinajs.cn/suggest/';
    const params = {
        type: '11,12',  // 11=沪深股票, 12=港股
        key: keyword
    };
    
    try {
        const response = await axios.get(url, {
            params: params,
            timeout: 5000,
            responseType: 'arraybuffer',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }
        });
        
        if (response.status === 200) {
            const rawData = iconv.decode(response.data, 'gbk');
            
            // 解析返回数据
            // 格式: var suggestvalue="茅台,11,600519,sh600519,贵州茅台,...";
            const match = rawData.match(/suggestvalue="(.+)";/);
            if (!match || !match[1]) {
                console.log('[Search] No match in response');
                return [];
            }
            
            const dataStr = match[1];
            const items = dataStr.split(',');
            
            const results = [];
            
            // 每5个元素一组：[名称, 类型, 代码, 全称, 中文名]
            for (let i = 0; i < items.length; i += 5) {
                if (i + 4 >= items.length) break;
                
                const name = items[i];      // "茅台"
                const type = items[i+1];    // "11" (沪深) 或 "12" (港股)
                const code = items[i+2];      // "600519"
                const fullCode = items[i+3];  // "sh600519"
                const fullName = items[i+4];  // "贵州茅台"
                
                // 判断市场
                let market = 'unknown';
                if (fullCode.startsWith('sh')) market = 'sh';
                else if (fullCode.startsWith('sz')) market = 'sz';
                else if (fullCode.startsWith('bj')) market = 'bj';
                else if (fullCode.startsWith('hk')) market = 'hk';
                else if (fullCode.startsWith('us')) market = 'us';
                
                results.push({
                    code: fullCode,
                    name: fullName || name,
                    market: market,
                    source: 'remote'
                });
            }
            
            return results;
        }
    } catch (error) {
        console.error('[Search API] Error:', error.message);
        return [];
    }
    
    return [];
}

// ========= SSE端点：/api/stream =========
app.get('/api/stream', function(req, res) {
    // 设置SSE头
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    });
    
    // 发送初始连接成功消息
    res.write('data: {"type":"connected"}\n\n');
    
    // 添加客户端到管理列表
    addSSEClient(res);
    
    // 启动后台任务（如果还没启动）
    startBackgroundTask();
    
    // 客户端断开连接
    req.on('close', function() {
        removeSSEClient(res);
    });
});

// ========= 路由定义 =========
app.get('/', function(req, res) {
    res.sendFile(path.join(__dirname, 'stock-monitor.html'));
});

app.get('/api/health', function(req, res) {
    res.json({status: 'ok'});
});

app.post('/api/stocks', async function(req, res) {
    try {
        var codes = req.body.codes;
        if (!codes || !Array.isArray(codes) || codes.length === 0) {
            return res.status(400).json({success: false, error: 'codes required'});
        }
        
        // 使用缓存获取数据
        var stocks = await getCachedStocks(codes);
        
        res.json({success: true, data: stocks});
    } catch (error) {
        console.error('API Error:', error);
        res.status(500).json({success: false, error: error.message});
    }
});

// ========= 新增：搜索股票API =========
app.get('/api/search-stocks', async function(req, res) {
    try {
        const keyword = req.query.q;
        if (!keyword || keyword.trim().length === 0) {
            return res.json({success: true, data: []});
        }
        
        console.log(`[Search] Remote search for: ${keyword}`);
        const results = await searchStocksFromAPI(keyword.trim());
        
        console.log(`[Search] Found ${results.length} results`);
        res.json({success: true, data: results});
    } catch (error) {
        console.error('[Search API] Error:', error);
        res.status(500).json({success: false, error: error.message});
    }
});

app.get('/api/stock-database', function(req, res) {
    const dbPath = path.join(__dirname, 'stock-database.json');
    res.sendFile(dbPath);
});

function parseStockData(rawData, codes) {
    var stocks = [];
    var lines = rawData.split(';');
    
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line || line.indexOf('=') === -1) continue;
        
        // 跳过无匹配结果的行（如 v_pv_none_match="1"）
        if (line.indexOf('pv_none_match') !== -1) continue;
        
        try {
            var match = line.match(/="(.+)"/);
            if (!match) continue;
            
            var fields = match[1].split('~');
            // 跳过无效数据：名称字段必须存在
            if (!fields[1]) continue;
            
            // 从返回行提取真实code（接口可能省略无效代码，不能用codes[i]）
            var codeMatch = line.match(/^v_([^=]+)=/);
            var code = (codeMatch && codeMatch[1]) || fields[2] || '';
            
            var stock = {
                code: code,
                name: fields[1] || '',
                currentPrice: parseFloat(fields[3]) || 0,
                change: parseFloat(fields[31]) || 0,
                changePercent: parseFloat(fields[32]) || 0,
                volume: parseInt(fields[6]) || 0,
                turnoverRate: parseFloat(fields[38]) || 0
            };
            stocks.push(stock);
        } catch (e) {
            console.error('Parse error:', e);
        }
    }
    return stocks;
}

const server = app.listen(PORT, HOST, function() {
    console.log('Server started at http://' + HOST + ':' + PORT);
});

server.on('error', function(error) {
    console.error('Server error:', error);
});
