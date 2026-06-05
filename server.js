const express = require('express');
const cors = require('cors');
const axios = require('axios');
const iconv = require('iconv-lite');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || '0.0.0.0';

// 禁用代理 — 本地开发环境代理不可用，直连腾讯/新浪 API
delete process.env.http_proxy;
delete process.env.HTTP_PROXY;
delete process.env.https_proxy;
delete process.env.HTTPS_PROXY;
delete process.env.no_proxy;
delete process.env.NO_PROXY;

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

// ========= 缓存层 =========
const cache = {
    data: null,           // 缓存的股票数据
    timestamp: 0,         // 缓存时间戳
    ttl: 3000,           // 缓存TTL：3秒
    updating: false,       // 是否正在更新
    key: ''                // 当前缓存对应的股票代码列表
};

let stockDatabaseIndex = null;

function normalizeCode(code) {
    var c = String(code || '').trim();
    // 美股代码：去掉后缀(.n/.oq/.ps等)，market前缀小写，ticker保持大写
    var usMatch = c.match(/^(us)([a-z]+)\.?[a-z0-9]*$/i);
    if (usMatch) return 'us' + usMatch[2].toUpperCase();
    // 其他市场统一小写
    return c.toLowerCase();
}

function decodeUnicode(str) {
    return (str || '').replace(/\\u([\dA-Fa-f]{4})/g, function(_, hex) {
        return String.fromCharCode(parseInt(hex, 16));
    });
}

function getCodesKey(codes) {
    return (codes || []).map(normalizeCode).join(',');
}

function getStockDatabaseIndex() {
    if (stockDatabaseIndex) return stockDatabaseIndex;

    stockDatabaseIndex = new Map();
    const dbPath = path.join(__dirname, 'stock-database.json');

    try {
        const stocks = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
        stocks.forEach(stock => {
            if (stock && stock.code) {
                stockDatabaseIndex.set(normalizeCode(stock.code), stock);
            }
        });
        console.log(`[Database] Loaded ${stockDatabaseIndex.size} local stocks`);
    } catch (error) {
        console.error('[Database] Load failed:', error.message);
    }

    return stockDatabaseIndex;
}

function createFallbackStock(code) {
    const normalizedCode = normalizeCode(code);
    const localStock = getStockDatabaseIndex().get(normalizedCode);

    return {
        code: normalizedCode || code,
        name: (localStock && localStock.name) || normalizedCode || code,
        currentPrice: 0,
        highPrice: 0,
        lowPrice: 0,
        change: 0,
        changePercent: 0,
        volume: 0,
        turnoverRate: 0,
        stale: true
    };
}

function completeStocks(codes, apiStocks) {
    const stocksByCode = new Map();

    (apiStocks || []).forEach(stock => {
        if (stock && stock.code) {
            stocksByCode.set(normalizeCode(stock.code), stock);
        }
    });

    return (codes || []).map(code => {
        const normalizedCode = normalizeCode(code);
        return stocksByCode.get(normalizedCode) || createFallbackStock(code);
    });
}

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
// 分类获取：A股用腾讯（实时），港美股用新浪（实时）
async function fetchStockDataFromAPI(codes) {
    const normalizedCodes = codes.map(normalizeCode);
    const tencentCodes = [];
    const sinaHkCodes = [];
    const sinaUsCodes = [];

    normalizedCodes.forEach(function(code) {
        if (/^hk/.test(code)) {
            sinaHkCodes.push(code);
        } else if (/^us/.test(code)) {
            sinaUsCodes.push(code);
        } else {
            tencentCodes.push(code);
        }
    });

    var results = [];

    // 腾讯：A股（实时）
    if (tencentCodes.length > 0) {
        try {
            const codesStr = tencentCodes.join(',');
            const url = 'http://qt.gtimg.cn/q=' + codesStr;
            const response = await axios.get(url, {
                responseType: 'arraybuffer',
                timeout: 10000
            });
            const data = iconv.decode(response.data, 'gbk');
            results = results.concat(parseStockData(data));
        } catch (error) {
            console.error('[Tencent API] A股获取失败:', error.message);
        }
    }

    // 新浪：港股（实时）
    if (sinaHkCodes.length > 0) {
        try {
            const hkStocks = await fetchFromSinaHK(sinaHkCodes);
            results = results.concat(hkStocks);
        } catch (error) {
            console.error('[Sina API] 港股获取失败:', error.message);
        }
    }

    // 新浪：美股（实时）
    if (sinaUsCodes.length > 0) {
        try {
            const usStocks = await fetchFromSinaUS(sinaUsCodes);
            results = results.concat(usStocks);
        } catch (error) {
            console.error('[Sina API] 美股获取失败:', error.message);
        }
    }

    return completeStocks(normalizedCodes, results);
}

async function fetchFromSinaHK(codes) {
    const symbols = codes.map(function(c) { return 'rt_hk' + c.replace(/^hk/, ''); }).join(',');
    const url = 'https://hq.sinajs.cn/list=' + symbols;

    const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 10000,
        headers: {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn/'
        }
    });

    const data = iconv.decode(response.data, 'gbk');
    const stocks = [];

    const lines = data.split('\n');
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line || line.indexOf('=') === -1) continue;

        try {
            var codeMatch = line.match(/rt_hk(\d+)=/);
            if (!codeMatch) continue;
            var code = 'hk' + codeMatch[1];

            var match = line.match(/="(.+)"/);
            if (!match) continue;

            var fields = match[1].split(',');
            if (fields.length < 13) continue;

            // 新浪 rt_hk 字段:
            // 0=英文名, 1=中文名, 2=今开, 3=昨收, 4=最高, 5=最低
            // 6=最新价, 7=涨跌额, 8=涨跌幅%, 11=成交额, 12=成交量(股)
            // 换手率：从腾讯补充数据中获取（腾讯虽延迟但股本数据是静态的）
            stocks.push({
                code: code,
                name: fields[1] || fields[0] || '',
                currentPrice: parseFloat(fields[6]) || 0,
                yesterdayClose: parseFloat(fields[3]) || 0,
                highPrice: parseFloat(fields[4]) || 0,
                lowPrice: parseFloat(fields[5]) || 0,
                change: parseFloat(fields[7]) || 0,
                changePercent: parseFloat(fields[8]) || 0,
                volume: parseInt(fields[12]) || 0,
                turnoverRate: 0  // 换手率后续从腾讯补
            });
        } catch (e) {
            console.error('[Sina HK] Parse error:', e.message);
        }
    }

    // 补充腾讯数据获取换手率（腾讯虽延迟，但换手率变化慢，可接受）
    if (stocks.length > 0) {
        try {
            const tencentCodes = stocks.map(function(s) { return s.code; }).join(',');
            const tencentUrl = 'http://qt.gtimg.cn/q=' + tencentCodes;
            const tencentResp = await axios.get(tencentUrl, {
                responseType: 'arraybuffer',
                timeout: 8000
            });
            const tencentData = iconv.decode(tencentResp.data, 'gbk');
            const tencentStocks = parseStockData(tencentData);
            
            // 用腾讯的换手率覆盖新浪数据
            const tencentMap = {};
            tencentStocks.forEach(function(ts) {
                tencentMap[normalizeCode(ts.code)] = ts;
            });
            stocks.forEach(function(s) {
                var key = normalizeCode(s.code);
                var ts = tencentMap[key];
                if (ts && ts.turnoverRate > 0) {
                    s.turnoverRate = ts.turnoverRate;
                }
            });
        } catch (e) {
            console.error('[Sina HK] 腾讯补数据失败:', e.message);
        }
    }

    console.log(`[Sina HK] 获取 ${stocks.length} 只港股`);
    return stocks;
}

async function fetchFromSinaUS(codes) {
    const symbols = codes.map(function(c) { return 'gb_' + c.replace(/^us/i, '').toLowerCase(); }).join(',');
    const url = 'https://hq.sinajs.cn/list=' + symbols;

    const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 10000,
        headers: {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn/'
        }
    });

    const data = iconv.decode(response.data, 'gbk');
    const stocks = [];

    const lines = data.split('\n');
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line || line.indexOf('=') === -1) continue;

        try {
            var codeMatch = line.match(/gb_(\w+)=/);
            if (!codeMatch) continue;
            var ticker = codeMatch[1].toUpperCase();
            var code = 'us' + ticker;

            var match = line.match(/="(.+)"/);
            if (!match) continue;

            var fields = match[1].split(',');
            if (fields.length < 10) continue;

            // 新浪 gb_ 字段（已验证）:
            // 0=名称, 1=最新价, 2=涨跌幅%, 3=时间, 4=涨跌额, 6=今开,
            // 7=最低, 8=最高, 10=成交量(股), 26=昨收
            stocks.push({
                code: code,
                name: fields[0] || ticker,
                currentPrice: parseFloat(fields[1]) || 0,
                yesterdayClose: parseFloat(fields[26]) || 0,
                highPrice: parseFloat(fields[8]) || 0,
                lowPrice: parseFloat(fields[7]) || 0,
                change: parseFloat(fields[4]) || 0,
                changePercent: parseFloat(fields[2]) || 0,
                volume: parseInt(fields[10]) || 0,
                turnoverRate: 0
            });
        } catch (e) {
            console.error('[Sina US] Parse error:', e.message);
        }
    }

    console.log(`[Sina US] 获取 ${stocks.length} 只美股`);
    return stocks;
}

// 获取缓存的股票数据（如果缓存过期则调用API）
async function getCachedStocks(codes) {
    const now = Date.now();
    const normalizedCodes = codes.map(normalizeCode);
    const key = getCodesKey(normalizedCodes);
    
    // 检查缓存是否有效
    if (cache.data && cache.key === key && (now - cache.timestamp) < cache.ttl) {
        console.log(`[Cache] Hit, age: ${now - cache.timestamp}ms`);
        return cache.data;
    }
    
    // 缓存过期或不存在，调用API
    console.log(`[Cache] Miss, fetching from API`);
    const stocks = await fetchStockDataFromAPI(normalizedCodes);
    
    // 更新缓存
    cache.data = stocks;
    cache.timestamp = now;
    cache.lastCodes = normalizedCodes;
    cache.key = key;
    
    return stocks;
}

// ========= 搜索股票API（代理腾讯财经搜索）=========
async function searchStocksFromAPI(keyword) {
    // 腾讯财经 smartbox 搜索API，覆盖面比新浪更广
    const url = 'https://smartbox.gtimg.cn/s3/';
    const params = {
        t: 'all',
        q: keyword
    };
    
    try {
        const response = await axios.get(url, {
            params: params,
            timeout: 5000,
            responseType: 'arraybuffer',
            maxRedirects: 5,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://finance.qq.com/'
            }
        });
        
        if (response.status === 200) {
            const rawData = iconv.decode(response.data, 'gbk');
            
            // 格式: v_hint="sz~300750~宁德时代~ndsd~GP-A^hk~03750~宁德时代~ndsd~GP^..."
            const match = rawData.match(/v_hint="(.+)"/);
            if (!match || !match[1]) {
                console.log('[Search] No match in response');
                return [];
            }
            
            const dataStr = match[1];
            const items = dataStr.split('^');
            
            const results = [];
            const seen = new Set();
            
            for (let i = 0; i < items.length; i++) {
                const parts = items[i].split('~');
                if (parts.length < 3) continue;
                
                const market = parts[0];  // sz / sh / hk / us
                const code = parts[1];    // 300750
                const name = parts[2];    // 宁德时代
                const pinyin = parts[3] || '';
                const type = parts[4] || '';
                
                // 只保留股票类型（GP）和ETF，过滤权证/债券等
                if (!type.startsWith('GP') && type !== 'ETF' && type !== 'LOF' && type !== 'REIT') continue;
                
                const fullCode = market + code;
                if (seen.has(fullCode)) continue;
                seen.add(fullCode);
                
                results.push({
                    code: fullCode,
                    name: decodeUnicode(name),
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

// ========= 搜索可转债API（东方财富搜索）=========
async function searchKZZFromEastMoney(keyword) {
    const url = 'https://searchadapter.eastmoney.com/api/suggest/get';
    const params = {
        input: keyword,
        type: 14,
        count: 10
    };
    
    try {
        const response = await axios.get(url, {
            params: params,
            timeout: 5000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://www.eastmoney.com/'
            }
        });
        
        if (response.status === 200 && response.data) {
            const data = response.data;
            const items = data.QuotationCodeTable && data.QuotationCodeTable.Data;
            if (!items || items.length === 0) return [];
            
            const results = [];
            const seen = new Set();
            
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                const code = item.Code;
                const name = item.Name;
                const marketType = item.MarketType; // 1=sh, 2=sz, 5=hk
                const secType = item.SecurityTypeName;
                
                // 只保留可转债（债券类型且代码以11/12开头）
                if (!code || !name) continue;
                var isKZZ = /^1[12]/.test(code);
                if (!isKZZ) continue;
                
                var prefix = marketType === '1' ? 'sh' : marketType === '2' ? 'sz' : '';
                if (!prefix) continue;
                
                var fullCode = prefix + code;
                if (seen.has(fullCode)) continue;
                seen.add(fullCode);
                
                results.push({
                    code: fullCode,
                    name: name,
                    market: prefix,
                    source: 'remote'
                });
            }
            
            return results;
        }
    } catch (error) {
        console.error('[KZZ Search API] Error:', error.message);
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
        
        console.log('[Search] Remote search for: ' + keyword);
        var results = await searchStocksFromAPI(keyword.trim());
        
        // smartbox 未找到结果时，尝试东方财富可转债搜索
        if (results.length === 0) {
            results = await searchKZZFromEastMoney(keyword.trim());
        }
        
        console.log('[Search] Found ' + results.length + ' results');
        res.json({success: true, data: results});
    } catch (error) {
        console.error('[Search API] Error:', error);
        res.status(500).json({success: false, error: error.message});
    }
});

// 大盘指数API
var INDEX_CODES = [
    'sh000001','sz399001','sz399006','sh000688','sh000016','bj899050',
    'sh000300','sh000905','sh000852','sz399330','sz399005',
    'sh000010','sh000903','sz399293','sz399106','sz399004','sz399011','sz399012','sh000842',
    'sh000827','sh000849','sh000932','sh000941','sh000979','sh000990','sh000991','sh000993','sz399015','sz399017',
    'hkHSI','hkHSTECH','hkHSCEI','hkHSCCI',
    'usDJI','usIXIC','usINX','usNDX',
    'fuGC','fuCL','fuSI','fuHG','fuNG','fuZC','fuRB',
    'fxUSDCNY','fxHKDCNY','fxUSDHKD','fxEURCNY','fxJPYCNY','fxGBPCNY','fxAUDCNY','fxCADCNY','fxSGDCNY','fxCHFCNY','fxTWDCNY','fxEURUSD','fxGBPUSD','fxUSDJPY',
    'sh000012','sh000013'
];
// 指数缓存：按请求的codes集合分组缓存，TTL 10秒（腾讯接口3-5秒更新一次）
var indexCache = {};
var INDEX_CACHE_TTL = 10000;

app.get('/api/indices', async function(req, res) {
    try {
        var now = Date.now();

        // 前端可传入 codes 参数，仅拉取需要的指数（大幅减少请求体积）
        var requestedCodes = req.query.codes ? req.query.codes.split(',') : INDEX_CODES;
        var cacheKey = requestedCodes.slice().sort().join(',');

        var cached = indexCache[cacheKey];
        if (cached && (now - cached.timestamp) < INDEX_CACHE_TTL) {
            return res.json({success: true, data: cached.data});
        }

        // 腾讯接口单次最大约60个，分批请求避免超时
        var allStocks = [];
        var BATCH_SIZE = 55;
        for (var i = 0; i < requestedCodes.length; i += BATCH_SIZE) {
            var batch = requestedCodes.slice(i, i + BATCH_SIZE);
            var url = 'http://qt.gtimg.cn/q=' + batch.join(',');
            var response = await axios.get(url, { responseType: 'arraybuffer', timeout: 8000 });
            var data = iconv.decode(response.data, 'gbk');
            allStocks = allStocks.concat(parseStockData(data));
        }

        indexCache[cacheKey] = { data: allStocks, timestamp: now };
        res.json({success: true, data: allStocks});
    } catch (error) {
        var cacheKey = (req.query.codes || INDEX_CODES.join(',')).split(',').slice().sort().join(',');
        if (indexCache[cacheKey]) {
            return res.json({success: true, data: indexCache[cacheKey].data});
        }
        // 兜底：尝试任一缓存
        var keys = Object.keys(indexCache);
        if (keys.length > 0) {
            return res.json({success: true, data: indexCache[keys[0]].data});
        }
        res.json({success: true, data: []});
    }
});

app.get('/api/stock-database', function(req, res) {
    const dbPath = path.join(__dirname, 'stock-database.json');
    res.sendFile(dbPath);
});

function parseStockData(rawData) {
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
            
            // 换手率：A股用fields[38]，港股用fields[59]
            var trField = /^hk/.test(code) ? 59 : 38;
            var stock = {
                code: code,
                name: fields[1] || '',
                currentPrice: parseFloat(fields[3]) || 0,
                yesterdayClose: parseFloat(fields[4]) || 0,
                highPrice: parseFloat(fields[33]) || 0,
                lowPrice: parseFloat(fields[34]) || 0,
                change: parseFloat(fields[31]) || 0,
                changePercent: parseFloat(fields[32]) || 0,
                volume: parseInt(fields[6]) || 0,
                turnoverRate: parseFloat(fields[trField]) || 0
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
    // 预热默认指数缓存（7个常用指数），首次页面加载直接命中
    var defaultCodes = ['sh000001','sz399001','sz399006','hkHSI','hkHSTECH','sh000300','sh000905'];
    var url = 'http://qt.gtimg.cn/q=' + defaultCodes.join(',');
    axios.get(url, { responseType: 'arraybuffer', timeout: 10000 }).then(function(response) {
        var data = iconv.decode(response.data, 'gbk');
        var stocks = parseStockData(data);
        var cacheKey = defaultCodes.slice().sort().join(',');
        indexCache[cacheKey] = { data: stocks, timestamp: Date.now() };
        console.log('Index cache warmed: ' + stocks.length + ' indices');
    }).catch(function(err) {
        console.log('Index warmup skipped (no network or offline)');
    });
});

server.on('error', function(error) {
    console.error('Server error:', error);
});
