const http = require('http');

// 测试健康检查
console.log('Testing health endpoint...');
http.get('<SIGNED_URL_REMOVED> (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
        console.log('Health check:', res.statusCode, data);
        
        // 测试股票API
        console.log('\nTesting stocks API...');
        const postData = JSON.stringify({codes: ['sh600519', 'sz000001']});
        
        const options = {
            hostname: '127.0.0.1',
            port: 3000,
            path: '/api/stocks',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };
        
        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                console.log('Stocks API:', res.statusCode);
                console.log('Response:', data.substring(0, 500));
                console.log('\nTest completed.');
            });
        });
        
        req.on('error', (e) => {
            console.error('Stocks API failed:', e.message);
        });
        
        req.write(postData);
        req.end();
    });
}).on('error', (e) => {
    console.error('Health check failed:', e.message);
});
