const http = require('http');

console.log('Testing API...\n');

// Test 1: Health check
const req1 = http.get('<SIGNED_URL_REMOVED>', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    console.log('Test 1 - Health check:');
    console.log('  Status:', res.statusCode);
    console.log('  Body:', data);
    console.log('');

    // Test 2: Stocks API
    const postData = JSON.stringify({ codes: ['sh600519', 'sz000001'] });
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

    const req2 = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        console.log('Test 2 - Stocks API:');
        console.log('  Status:', res.statusCode);
        console.log('  Body (first 500 chars):', data.substring(0, 500));
        console.log('\n✅ API tests completed!');
      });
    });

    req2.on('error', (e) => {
      console.error('Test 2 failed:', e.message);
    });

    req2.write(postData);
    req2.end();
  });
});

req1.on('error', (e) => {
  console.error('Test 1 failed:', e.message);
});
