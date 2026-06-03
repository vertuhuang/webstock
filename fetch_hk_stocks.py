#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取港股全量数据
数据来源：腾讯财经API - 通过搜索接口获取港股列表
"""

import json
import requests
import time
import re

def search_hk_stocks_keyword(keyword, page=1):
    """通过关键词搜索港股"""
    url = "https://smartbox.gtimg.cn/s3/"
    params = {
        'q': keyword,
        't': 'gp',
        'format': 'json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://gu.qq.com/',
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    异常: {e}")
        return None

def get_hk_stocks_from_tencent():
    """从腾讯财经获取港股列表 - 通过多个关键词搜索"""
    print("正在从腾讯财经获取港股数据...")
    stocks_dict = {}  # 用字典去重
    
    # 尝试多个关键词来获取港股
    # 港股代码通常以0开头（如00700）或1开头（如10318）
    keywords = []
    
    # 生成关键词：0-9 + 00-99 + 000-999
    # 港股代码格式：5位数字，如00700, 09988
    for i in range(10):
        keywords.append(str(i))
    for i in range(100):
        keywords.append(f"{i:02d}")
    
    print(f"  准备使用 {len(keywords)} 个关键词搜索...")
    
    successful_searches = 0
    for idx, keyword in enumerate(keywords):
        if idx % 20 == 0:
            print(f"    进度: {idx}/{len(keywords)} ({idx*100//len(keywords)}%)", end='\r', flush=True)
        
        data = search_hk_stocks_keyword(keyword)
        
        if data and 'gp' in data:
            gp_list = data['gp']
            if gp_list and len(gp_list) > 0:
                successful_searches += 1
                for item in gp_list:
                    # item格式: ["港股", "00700", "腾讯控股", "hk00700"]
                    if len(item) >= 4 and item[3].startswith('hk'):
                        code = item[1]  # 代码：00700
                        name = item[2]  # 名称：腾讯控股
                        full_code = item[3]  # hk00700
                        
                        if full_code not in stocks_dict:
                            stocks_dict[full_code] = {
                                'code': full_code,
                                'name': name,
                                'market': 'hk'
                            }
        
        time.sleep(0.1)  # 避免请求过快
    
    print(f"\n  搜索完成，成功 {successful_searches}/{len(keywords)} 次")
    print(f"  获取到 {len(stocks_dict)} 只港股")
    
    return list(stocks_dict.values())

def get_hk_stocks_from_163():
    """从网易财经获取港股列表"""
    print("正在从网易财经获取港股数据...")
    stocks = []
    
    # 网易财经港股API
    url = "https://quotes.money.163.com/hkstock/hklist.json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://money.163.com/',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"  获取到 {len(data)} 只港股")
            
            for item in data:
                code = item.get('symbol', '')  # 代码：00700
                name = item.get('name', '')   # 名称：腾讯控股
                
                if code and name:
                    full_code = f"hk{code}"
                    stocks.append({
                        'code': full_code,
                        'name': name,
                        'market': 'hk'
                    })
    except Exception as e:
        print(f"  异常: {e}")
    
    return stocks

def get_hk_stocks_manual():
    """手动添加港股列表 - 恒生指数成分股 + 活跃港股"""
    print("使用手动添加的港股列表...")
    
    hk_stocks = [
        # 恒生指数成分股 (HSI)
        ('00700', '腾讯控股'), ('00941', '中国移动'), ('01398', '工商银行'),
        ('01810', '小米集团-W'), ('03690', '美团-W'), ('09988', '阿里巴巴-W'),
        ('00388', '香港交易所'), ('01299', '友邦保险'), ('00005', '汇丰控股'),
        ('01024', '快手-W'), ('02318', '中国平安'), ('09626', '哔哩哔哩-W'),
        ('09888', '百度集团-W'), ('00241', '阿里健康'), ('01177', '中国生物制药'),
        ('09618', '京东集团-W'), ('02020', '安踏体育'), ('00992', '联想集团'),
        ('00883', '中国海洋石油'), ('02382', '舜宇光学科技'), ('09999', '网易-W'),
        ('01797', '新东方-S'), ('01833', '平安好医生'), ('06186', '中国飞鹤'),
        ('00285', '比亚迪电子'), ('02382', '舜宇光学科技'), ('09618', '京东集团-SW'),
        ('00939', '建设银行'), ('01398', '工商银行'), ('02318', '中国平安'),
        ('03988', '中国银行'), ('01299', '友邦保险'), ('00011', '恒生银行'),
        ('00012', '恒基地产'), ('00016', '新鸿基地产'), ('00017', '新世界发展'),
        ('00019', '太古股份公司A'), ('00027', '银河娱乐'), ('00066', '港铁公司'),
        ('00083', '信和置业'), ('00101', '恒隆地产'), ('00116', '周生生'),
        ('00135', '昆仑能源'), ('00144', '招商局港口'), ('00151', '中国旺旺'),
        ('00175', '吉利汽车'), ('00267', '中信股份'), ('00293', '国泰航空'),
        ('00322', '康师傅控股'), ('00323', '马鞍山钢铁股份'), ('00338', '上海石化'),
        ('00368', '中港石油'), ('00386', '中国石油化工股份'), ('00388', '香港交易所'),
        ('00400', ' contributed by computer'), ('00417', '谢瑞麟'), ('00460', '四环医药'),
        ('00489', '东风集团股份'), ('00494', '利丰'), ('00511', '电视广播'),
        ('00522', 'ASM太平洋'), ('00546', '阜丰集团'), ('00551', '裕元集团'),
        ('00552', '中国通信服务'), ('00553', '南京熊猫电子股份'), ('00576', '浙江沪杭甬'),
        ('00586', '海螺创业'), ('00587', '海螺水泥'), ('00590', '六福集团'),
        ('00593', '星岛'), ('00612', '中国投资基金'), ('00669', '创科实业'),
        ('00688', '中芯国际'), ('00694', '北京首都机场股份'), ('00696', '中国民航信息网络'),
        ('00700', '腾讯控股'), ('00753', '中国国航'), ('00762', '中国联通'),
        ('00787', '利标品牌'), ('00809', '大成糖业'), ('00823', '领展房产基金'),
        ('00836', '华润电力'), ('00857', '中国石油股份'), ('00868', '信义能源'),
        ('00871', '中国宏桥'), ('00883', '中国海洋石油'), ('00914', '安徽海螺水泥'),
        ('00921', '海信家电'), ('00939', '建设银行'), ('00941', '中国移动'),
        ('00992', '联想集团'), ('00998', '中信银行'), ('01024', '快手-W'),
        ('01038', '长江基建集团'), ('01044', '恒安国际'), ('01052', '越秀交通基建'),
        ('01053', '重庆燃气'), ('01056', '中国中药'), ('01070', 'TCL多媒体'),
        ('01072', '东方电气'), ('01093', '石药集团'), ('01109', '华润置地'),
        ('01113', '长江生命科技'), ('01117', '现代牧业'), ('01138', '中远海发'),
        ('01157', '中联重科'), ('01177', '中国生物制药'), ('01186', '中国铁建'),
        ('01205', '中信资源'), ('01209', '华润万象生活'), ('01211', '比亚迪股份'),
        ('01238', '霸王集团'), ('01250', '北控水务集团'), ('01270', '朗廷-SS'),
        ('01288', '农业银行'), ('01299', '友邦保险'), ('01302', '先健科技'),
        ('01308', '海天国际'), ('01310', '香港宽频'), ('01316', '耐世特'),
        ('01317', '枫叶教育'), ('01336', '新华保险'), ('01339', '中国人民保险集团'),
        ('01359', '中国信达'), ('01368', '特步国际'), ('01378', '中国宏泰发展'),
        ('01382', '鸿宝资源'), ('01385', '环球医疗'), ('01398', '工商银行'),
        ('01432', '恒腾网络'), ('01448', '福寿园'), ('01452', '迪诺斯环保'),
        ('01458', '周黑鸭'), ('01462', '金诚控股'), ('01478', '丘钛科技'),
        ('01508', '中国再保险'), ('01513', '丽珠医药'), ('01515', '华润医疗'),
        ('01528', '红星美凯龙'), ('01530', '三生制药'), ('01548', '金斯瑞生物科技'),
        ('01579', '颐海国际'), ('01585', '雅迪控股'), ('01600', '天伦燃气'),
        ('01608', '伟能集团'), ('01638', '佳兆业集团'), ('01658', '邮储银行'),
        ('01668', '华南城'), ('01680', '澳门励骏'), ('01717', '澳优'),
        ('01728', '正通汽车'), ('01755', '新城悦服务'), ('01772', '赣锋锂业'),
        ('01776', '广发证券'), ('01797', '新东方-S'), ('01800', '中国交通建设'),
        ('01810', '小米集团-W'), ('01812', '晨鸣纸业'), ('01816', '中广核电力'),
        ('01818', '招金矿业'), ('01833', '平安好医生'), ('01860', '汇付天下'),
        ('01873', '维亚生物'), ('01876', '百威亚太'), ('01880', '中国中免'),
        ('01898', '中国有色金属'), ('01911', '华兴资本控股'), ('01918', '融创中国'),
        ('01928', '金沙中国'), ('01951', '锦欣生殖'), ('01952', '云顶新耀-B'),
        ('01958', '北京汽车'), ('01963', '重庆银行'), ('01966', '中骏集团'),
        ('01970', 'IMAX中国'), ('01972', '赣锋锂业'), ('01988', '民生银行'),
        ('01999', '敏华控股'), ('02005', '石四药集团'), ('02013', '微盟集团'),
        ('02018', '瑞声科技'), ('02020', '安踏体育'), ('02039', '中集集团'),
        ('02318', '中国平安'), ('02319', '蒙牛乳业'), ('02328', '中国财险'),
        ('02338', '潍柴动力'), ('02348', '东瀛游'), ('02356', '大昌行集团'),
        ('02358', '中软国际'), ('02368', '中骏商管'), ('02380', '中国电力'),
        ('02382', '舜宇光学科技'), ('02383', '日本城控股'), ('02386', '中石化油服'),
        ('02388', '中银香港'), ('02400', '心动公司'), ('09988', '阿里巴巴-W'),
        ('09999', '网易-S'),
    ]
    
    stocks = []
    for code, name in hk_stocks:
        stocks.append({'code': f'hk{code}', 'name': name, 'market': 'hk'})
    
    print(f"  手动添加了 {len(stocks)} 只港股")
    return stocks

def main():
    print("=" * 60)
    print("开始获取港股全量数据")
    print("=" * 60)
    
    all_hk_stocks = []
    
    # 方法1：腾讯财经搜索API
    print("\n[方法1] 腾讯财经搜索API")
    tencent_stocks = get_hk_stocks_from_tencent()
    all_hk_stocks.extend(tencent_stocks)
    print(f"当前总计: {len(all_hk_stocks)} 只港股\n")
    
    # 如果腾讯API没获取到足够数据，使用手动列表
    if len(all_hk_stocks) < 100:
        print("\n[方法2] 手动添加港股列表")
        manual_stocks = get_hk_stocks_manual()
        # 合并去重
        existing_codes = set(s['code'] for s in all_hk_stocks)
        for stock in manual_stocks:
            if stock['code'] not in existing_codes:
                all_hk_stocks.append(stock)
                existing_codes.add(stock['code'])
        print(f"合并后总计: {len(all_hk_stocks)} 只港股\n")
    
    # 保存港股数据到单独文件（用于合并）
    output_file = '/Users/vertu/Desktop/Project/webstock/hk-stock-database.json'
    print(f"\n正在保存港股数据到 {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_hk_stocks, f, ensure_ascii=False, indent=2)
    
    print("✅ 保存成功！")
    print(f"\n📊 港股统计: {len(all_hk_stocks)} 只")
    print("=" * 60)

if __name__ == '__main__':
    main()
