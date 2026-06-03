#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取全量A股和港股数据，保存到 stock-database.json
数据来源：
1. A股：东方财富API
2. 港股：腾讯财经API
"""

import json
import requests
import time

def get_a_stocks():
    """获取A股列表（沪深北交所+科创板+创业板）"""
    print("正在获取A股数据...")
    stocks = []
    
    # 东方财富API - 获取沪深A股+科创板+创业板+北交所
    # fs参数说明：
    # m:0+t:6 = 深圳A股
    # m:0+t:80 = 深圳科创板
    # m:0+t:81 = 深圳创业板
    # m:1+t:2 = 上海A股  
    # m:1+t:23 = 上海科创板
    # m:0+t:90 = 北交所A股
    url = "http://80.push2.eastmoney.com/api/qt/clist/get"
    
    params = {
        'pn': 1,
        'pz': 5000,  # 每页5000条，一次获取
        'po': 1,
        'np': 1,
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': 2,
        'invt': 2,
        'fid': 'f3',
        'fs': 'm:0+t:6,m:0+t:80,m:0+t:81,m:1+t:2,m:1+t:23,m:0+t:90',
        'fields': 'f12,f13,f14'  # f12=代码, f13=市场, f14=名称
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data['rc'] == 0 and 'data' in data and data['data']:
            stock_list = data['data']['diff']
            print(f"获取到 {len(stock_list)} 只A股")
            
            for item in stock_list:
                code = item['f12']
                name = item['f14']
                market_code = item['f13']  # 0=深市, 1=沪市
                
                # 转换市场标识
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
            print(f"获取A股数据失败: {data}")
    except Exception as e:
        print(f"获取A股数据异常: {e}")
    
    return stocks

def get_hk_stocks():
    """获取港股列表"""
    print("正在获取港股数据...")
    stocks = []
    
    # 尝试多个数据源
    # 方法1: 腾讯财经港股列表
    try:
        # 港股主板列表
        url = "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?_var=kline_dayqfq&param=hk00700,day,,,10,qfq"
        # 这个API不适合批量获取，换一个
        
        # 方法2: 使用东方财富港股API
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
            'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',  # 港股
            'fields': 'f12,f13,f14'
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data['rc'] == 0 and 'data' in data and data['data']:
            stock_list = data['data']['diff']
            print(f"获取到 {len(stock_list)} 只港股")
            
            for item in stock_list:
                code = item['f12']
                name = item['f14']
                
                # 港股代码格式：00700
                full_code = f"hk{code}"
                
                stocks.append({
                    'code': full_code,
                    'name': name,
                    'market': 'hk'
                })
        else:
            print(f"获取港股数据失败: {data}")
    except Exception as e:
        print(f"获取港股数据异常: {e}")
    
    return stocks

def get_us_stocks():
    """获取美股列表（可选）"""
    print("正在获取美股数据...")
    stocks = []
    
    try:
        # 东方财富美股API
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
            'fs': 'm:105',  # 美股
            'fields': 'f12,f13,f14'
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data['rc'] == 0 and 'data' in data and data['data']:
            stock_list = data['data']['diff']
            print(f"获取到 {len(stock_list)} 只美股")
            
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
        print(f"获取美股数据异常: {e}")
    
    return stocks

def main():
    print("=" * 60)
    print("开始获取全量股票数据")
    print("=" * 60)
    
    all_stocks = []
    
    # 获取A股
    a_stocks = get_a_stocks()
    all_stocks.extend(a_stocks)
    print(f"当前总计: {len(all_stocks)} 只股票\n")
    
    time.sleep(1)  # 避免请求过快
    
    # 获取港股
    hk_stocks = get_hk_stocks()
    all_stocks.extend(hk_stocks)
    print(f"当前总计: {len(all_stocks)} 只股票\n")
    
    time.sleep(1)
    
    # 获取美股（可选）
    us_stocks = get_us_stocks()
    all_stocks.extend(us_stocks)
    print(f"当前总计: {len(all_stocks)} 只股票\n")
    
    # 去重（根据code）
    print("正在去重...")
    seen_codes = set()
    unique_stocks = []
    for stock in all_stocks:
        if stock['code'] not in seen_codes:
            seen_codes.add(stock['code'])
            unique_stocks.append(stock)
    
    print(f"去重后: {len(unique_stocks)} 只股票")
    
    # 保存到文件
    output_file = '/Users/vertu/Desktop/Project/webstock/stock-database.json'
    print(f"\n正在保存到 {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_stocks, f, ensure_ascii=False, indent=2)
    
    print("✅ 保存成功！")
    print(f"\n统计信息:")
    print(f"  A股: {len(a_stocks)} 只")
    print(f"  港股: {len(hk_stocks)} 只")
    print(f"  美股: {len(us_stocks)} 只")
    print(f"  总计: {len(unique_stocks)} 只")
    print("=" * 60)

if __name__ == '__main__':
    main()
