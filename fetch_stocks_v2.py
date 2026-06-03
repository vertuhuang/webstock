#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取全量A股和港股数据，保存到 stock-database.json
数据来源：东方财富API
"""

import json
import requests
import time
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_a_stocks():
    """获取A股列表（沪深北交所+科创板+创业板）"""
    print("正在获取A股数据...")
    stocks = []
    
    # 使用Session保持连接
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://quote.eastmoney.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    
    # 东方财富API - 分多次获取，每次获取不同市场
    markets = [
        ('m:0+t:6', '深圳A股'),
        ('m:0+t:80', '深圳科创板'),
        ('m:0+t:81', '深圳创业板'),
        ('m:1+t:2', '上海A股'),
        ('m:1+t:23', '上海科创板'),
        ('m:0+t:90', '北交所A股'),
    ]
    
    for fs_code, market_name in markets:
        print(f"  正在获取{market_name}...")
        url = "http://80.push2.eastmoney.com/api/qt/clist/get"
        
        params = {
            'pn': 1,
            'pz': 5000,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': fs_code,
            'fields': 'f12,f13,f14'
        }
        
        try:
            response = session.get(url, params=params, timeout=30, verify=False)
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data and data['data']:
                stock_list = data['data'].get('diff', [])
                print(f"    获取到 {len(stock_list)} 只{market_name}")
                
                for item in stock_list:
                    code = item['f12']
                    name = item['f14']
                    market_code = item['f13']
                    
                    if market_code == 0:  # 深圳
                        market = 'sz'
                        full_code = f"sz{code}"
                    elif market_code == 1:  # 上海
                        market = 'sh'
                        full_code = f"sh{code}"
                    else:
                        continue
                    
                    stocks.append({
                        'code': full_code,
                        'name': name,
                        'market': market
                    })
            else:
                print(f"    获取{market_name}失败: {data.get('msg', '未知错误')}")
        except Exception as e:
            print(f"    获取{market_name}异常: {e}")
        
        time.sleep(0.5)  # 避免请求过快
    
    print(f"  A股总计: {len(stocks)} 只")
    return stocks

def get_hk_stocks():
    """获取港股列表"""
    print("正在获取港股数据...")
    stocks = []
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'http://quote.eastmoney.com/',
    })
    
    # 东方财富港股API
    markets = [
        ('m:128+t:3', '港股主板'),
        ('m:128+t:4', '港股创业板'),
        ('m:128+t:1', '港股蓝筹'),
        ('m:128+t:2', '港股红筹'),
    ]
    
    for fs_code, market_name in markets:
        print(f"  正在获取{market_name}...")
        url = "http://80.push2.eastmoney.com/api/qt/clist/get"
        
        params = {
            'pn': 1,
            'pz': 5000,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': fs_code,
            'fields': 'f12,f13,f14'
        }
        
        try:
            response = session.get(url, params=params, timeout=30, verify=False)
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data and data['data']:
                stock_list = data['data'].get('diff', [])
                print(f"    获取到 {len(stock_list)} 只{market_name}")
                
                for item in stock_list:
                    code = item['f12']
                    name = item['f14']
                    
                    full_code = f"hk{code}"
                    
                    stocks.append({
                        'code': full_code,
                        'name': name,
                        'market': 'hk'
                    })
        except Exception as e:
            print(f"    获取{market_name}异常: {e}")
        
        time.sleep(0.5)
    
    print(f"  港股总计: {len(stocks)} 只")
    return stocks

def get_us_stocks():
    """获取美股列表"""
    print("正在获取美股数据...")
    stocks = []
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'http://quote.eastmoney.com/',
    })
    
    try:
        url = "http://80.push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': 1,
            'pz': 5000,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:105',
            'fields': 'f12,f13,f14'
        }
        
        response = session.get(url, params=params, timeout=30, verify=False)
        data = response.json()
        
        if data.get('rc') == 0 and 'data' in data and data['data']:
            stock_list = data['data'].get('diff', [])
            print(f"  获取到 {len(stock_list)} 只美股")
            
            for item in stock_list:
                code = item['f12']
                name = item['f14']
                
                full_code = f"us{code}"
                
                stocks.append({
                    'code': full_code,
                    'name': name,
                    'market': 'us'
                })
    except Exception as e:
        print(f"  获取美股异常: {e}")
    
    return stocks

def main():
    print("=" * 60)
    print("开始获取全量股票数据")
    print("=" * 60)
    
    all_stocks = []
    
    # 获取A股
    print("\n[1/3] 获取A股数据")
    a_stocks = get_a_stocks()
    all_stocks.extend(a_stocks)
    print(f"当前总计: {len(all_stocks)} 只股票\n")
    
    # 获取港股
    print("\n[2/3] 获取港股数据")
    hk_stocks = get_hk_stocks()
    all_stocks.extend(hk_stocks)
    print(f"当前总计: {len(all_stocks)} 只股票\n")
    
    # 获取美股
    print("\n[3/3] 获取美股数据")
    us_stocks = get_us_stocks()
    all_stocks.extend(us_stocks)
    print(f"当前总计: {len(all_stocks)} 只股票\n")
    
    # 去重
    print("正在去重...")
    seen_codes = set()
    unique_stocks = []
    for stock in all_stocks:
        if stock['code'] not in seen_codes:
            seen_codes.add(stock['code'])
            unique_stocks.append(stock)
    
    print(f"去重后: {len(unique_stocks)} 只股票")
    
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
