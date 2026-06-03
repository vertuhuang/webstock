#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取全量A股和港股数据，保存到 stock-database.json
数据来源：新浪财经API
"""

import json
import requests
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_sina_api(node, page=1, num=5000):
    """调用新浪财经API获取数据"""
    url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    params = {
        'page': page,
        'num': num,
        'sort': 'symbol',
        'asc': 1,
        'node': node,
        '_s_r_a': 'init'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'http://finance.sina.com.cn/',
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    异常: {e}")
        return None

def get_a_stocks():
    """获取A股列表（沪深北交所）"""
    print("正在获取A股数据...")
    stocks = []
    
    # 新浪财经节点：hs_a = 沪深A股（包含沪深北交所）
    nodes = [
        ('hs_a', '沪深A股'),
    ]
    
    for node, name in nodes:
        print(f"  正在获取{name}...")
        
        # 新浪API一次最多返回5000条，需要分页
        page = 1
        while True:
            print(f"    第{page}页...", end='')
            data = fetch_sina_api(node, page=page, num=5000)
            
            if not data or len(data) == 0:
                print("无数据")
                break
            
            print(f"{len(data)}条")
            
            for item in data:
                symbol = item['symbol']  # 格式：sh600519, sz000001, bj920000
                code = item['code']      # 代码：600519, 000001, 920000
                name = item['name']      # 名称
                
                # 判断市场
                if symbol.startswith('sh'):
                    market = 'sh'
                    full_code = f"sh{code}"
                elif symbol.startswith('sz'):
                    market = 'sz'
                    full_code = f"sz{code}"
                elif symbol.startswith('bj'):
                    market = 'bj'
                    full_code = f"bj{code}"
                else:
                    continue
                
                stocks.append({
                    'code': full_code,
                    'name': name,
                    'market': market
                })
            
            # 如果返回数据少于5000条，说明已经是最后一页
            if len(data) < 5000:
                break
            
            page += 1
            time.sleep(0.3)  # 避免请求过快
        
        print(f"  {name}总计: {len(stocks)} 只")
    
    return stocks

def get_hk_stocks():
    """获取港股列表"""
    print("正在获取港股数据...")
    stocks = []
    
    # 新浪财经港股节点
    nodes = [
        ('hk_s', '港股'),
    ]
    
    for node, name in nodes:
        print(f"  正在获取{name}...")
        
        page = 1
        while True:
            print(f"    第{page}页...", end='')
            data = fetch_sina_api(node, page=page, num=5000)
            
            if not data or len(data) == 0:
                print("无数据")
                break
            
            print(f"{len(data)}条")
            
            for item in data:
                symbol = item['symbol']  # 格式：hk00700
                code = item['code']      # 代码：00700
                name = item['name']      # 名称
                
                full_code = f"hk{code}"
                
                stocks.append({
                    'code': full_code,
                    'name': name,
                    'market': 'hk'
                })
            
            if len(data) < 5000:
                break
            
            page += 1
            time.sleep(0.3)
        
        print(f"  {name}总计: {len(stocks)} 只")
    
    return stocks

def get_us_stocks():
    """获取美股列表"""
    print("正在获取美股数据...")
    stocks = []
    
    nodes = [
        ('us_s', '美股'),
    ]
    
    for node, name in nodes:
        print(f"  正在获取{name}...")
        
        page = 1
        while True:
            print(f"    第{page}页...", end='')
            data = fetch_sina_api(node, page=page, num=5000)
            
            if not data or len(data) == 0:
                print("无数据")
                break
            
            print(f"{len(data)}条")
            
            for item in data:
                symbol = item['symbol']  # 格式：usAAPL
                code = item['code']      # 代码：AAPL
                name = item['name']      # 名称
                
                full_code = f"us{code}"
                
                stocks.append({
                    'code': full_code,
                    'name': name,
                    'market': 'us'
                })
            
            if len(data) < 5000:
                break
            
            page += 1
            time.sleep(0.3)
        
        print(f"  {name}总计: {len(stocks)} 只")
    
    return stocks

def main():
    print("=" * 60)
    print("开始获取全量股票数据（新浪财经API）")
    print("=" * 60)
    
    all_stocks = []
    
    # 获取A股
    print("\n[1/3] 获取A股数据")
    a_stocks = get_a_stocks()
    all_stocks.extend(a_stocks)
    print(f"\n当前总计: {len(all_stocks)} 只股票\n")
    
    time.sleep(1)
    
    # 获取港股
    print("\n[2/3] 获取港股数据")
    hk_stocks = get_hk_stocks()
    all_stocks.extend(hk_stocks)
    print(f"\n当前总计: {len(all_stocks)} 只股票\n")
    
    time.sleep(1)
    
    # 获取美股
    print("\n[3/3] 获取美股数据")
    us_stocks = get_us_stocks()
    all_stocks.extend(us_stocks)
    print(f"\n当前总计: {len(all_stocks)} 只股票\n")
    
    # 去重
    print("正在去重...")
    seen_codes = set()
    unique_stocks = []
    duplicates = 0
    
    for stock in all_stocks:
        if stock['code'] not in seen_codes:
            seen_codes.add(stock['code'])
            unique_stocks.append(stock)
        else:
            duplicates += 1
    
    print(f"去重后: {len(unique_stocks)} 只股票 (删除{duplicates}个重复)")
    
    # 保存
    output_file = '/Users/vertu/Desktop/Project/webstock/stock-database.json'
    print(f"\n正在保存到 {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_stocks, f, ensure_ascii=False, indent=2)
    
    print("✅ 保存成功！")
    print(f"\n📊 统计信息:")
    print(f"  A股: {len(a_stocks)} 只")
    print(f"  港股: {len(hk_stocks)} 只")
    print(f"  美股: {len(us_stocks)} 只")
    print(f"  总计: {len(unique_stocks)} 只")
    print("=" * 60)

if __name__ == '__main__':
    main()
