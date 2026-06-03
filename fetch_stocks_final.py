#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取全量A股数据，保存到 stock-database.json
数据来源：新浪财经API (分页获取)
"""

import json
import requests
import time
import sys

def fetch_sina_api(node, page=1, num=100):
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
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    异常: {e}")
        return None

def get_a_stocks():
    """获取A股列表（沪深北交所）- 分页获取"""
    print("正在获取A股数据...")
    stocks = []
    
    # 新浪财经节点：hs_a = 沪深A股（包含沪深北交所）
    node = 'hs_a'
    print(f"  节点: {node}")
    
    page = 1
    total_pages = None
    
    while True:
        print(f"    第{page}页...", end='', flush=True)
        data = fetch_sina_api(node, page=page, num=100)
        
        if not data or len(data) == 0:
            print("无数据，停止")
            break
        
        print(f"{len(data)}条", flush=True)
        
        for item in data:
            symbol = item.get('symbol', '')  # 格式：sh600519, sz000001, bj920000
            code = item.get('code', '')      # 代码：600519, 000001, 920000
            name = item.get('name', '')      # 名称
            
            if not symbol or not code or not name:
                continue
            
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
        
        # 如果返回数据少于100条，说明已经是最后一页
        if len(data) < 100:
            print(f"  已到最后一页 (第{page}页)")
            break
        
        page += 1
        time.sleep(0.5)  # 避免请求过快
        
        # 安全限制：最多获取1000页（10万条）
        if page > 1000:
            print("  达到安全限制(1000页)，停止")
            break
    
    print(f"  A股总计: {len(stocks)} 只")
    return stocks

def get_hk_stocks_from_eastmoney():
    """从东方财富获取港股列表（分页获取全量）"""
    print("正在从东方财富获取港股数据...")
    stocks = []
    
    url = "http://push2his.eastmoney.com/api/qt/clist/get"
    print(f"  使用API: {url}")
    
    page = 1
    while True:
        print(f"    第{page}页...", end='', flush=True)
        try:
            params = {
                'pn': page,
                'pz': 100,  # 东方财富API每页100条
                'po': 1,
                'np': 1,
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',
                'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',
                'fields': 'f12,f13,f14',
                '_': int(time.time() * 1000)
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'http://quote.eastmoney.com/',
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"HTTP {response.status_code}")
                break
            
            data = response.json()
            
            if data.get('rc') != 0 or 'data' not in data or not data['data']:
                print("无数据")
                break
            
            stock_list = data['data'].get('diff', [])
            print(f"{len(stock_list)}条", flush=True)
            
            if not stock_list:
                print("空列表，停止")
                break
            
            for item in stock_list:
                code = item['f12']
                name = item['f14']
                full_code = f"hk{code}"
                
                stocks.append({
                    'code': full_code,
                    'name': name,
                    'market': 'hk'
                })
            
            page += 1
            time.sleep(0.5)
            
            # 安全限制
            if page > 100:
                print("  达到安全限制(100页)，停止")
                break
                
        except Exception as e:
            print(f"异常: {e}")
            break
    
    if not stocks:
        print("  东方财富API失败，使用手动添加的主要港股...")
        manual_hk = [
            ('00700', '腾讯控股'), ('00941', '中国移动'), ('01398', '工商银行'),
            ('01810', '小米集团-W'), ('03690', '美团-W'), ('09988', '阿里巴巴-SW'),
            ('00388', '香港交易所'), ('01299', '友邦保险'), ('00005', '汇丰控股'),
            ('01024', '快手-W'), ('06603', '中信股份'), ('02318', '中国平安'),
            ('01093', '石药集团'), ('09626', '哔哩哔哩-SW'), ('09888', '百度集团-SW'),
            ('00241', '阿里健康'), ('01072', '东方电气'), ('01177', '中国生物制药'),
            ('09618', '京东集团-SW'), ('02020', '安踏体育'), ('00992', '联想集团'),
            ('00883', '中国海洋石油'), ('01093', '石药集团'), ('02382', '舜宇光学科技'),
            ('00285', '比亚迪电子'), ('01797', '新东方-S'), ('09999', '网易-S'),
            ('01833', '平安好医生'), ('06186', '中国飞鹤'), ('00291', '华润啤酒'),
        ]
        for code, name in manual_hk:
            stocks.append({'code': f'hk{code}', 'name': name, 'market': 'hk'})
        print(f"  手动添加了 {len(stocks)} 只主要港股")
    else:
        print(f"  港股总计: {len(stocks)} 只")
    
    return stocks

def main():
    print("=" * 60)
    print("开始获取股票数据")
    print("=" * 60)
    
    all_stocks = []
    
    # 获取A股
    print("\n[1/2] 获取A股数据（新浪财经API）")
    a_stocks = get_a_stocks()
    all_stocks.extend(a_stocks)
    print(f"\n当前总计: {len(all_stocks)} 只股票\n")
    
    time.sleep(1)
    
    # 获取港股
    print("\n[2/2] 获取港股数据（东方财富API + 手动补充）")
    hk_stocks = get_hk_stocks_from_eastmoney()
    all_stocks.extend(hk_stocks)
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
    
    # 按市场统计
    market_stats = {}
    for stock in unique_stocks:
        market = stock['market']
        market_stats[market] = market_stats.get(market, 0) + 1
    
    # 保存
    output_file = '/Users/vertu/Desktop/Project/webstock/stock-database.json'
    print(f"\n正在保存到 {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_stocks, f, ensure_ascii=False, indent=2)
    
    print("✅ 保存成功！")
    print(f"\n📊 统计信息:")
    for market, count in sorted(market_stats.items()):
        print(f"  {market}: {count} 只")
    print(f"  总计: {len(unique_stocks)} 只")
    print("=" * 60)

if __name__ == '__main__':
    main()
