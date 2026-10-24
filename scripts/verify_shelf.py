#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦积分真账本 · 货架验真器 (Shelf Auditor)
==============================================

对麦当劳积分商城做"去伪"核算，回答三个问题：

  1. 官方接口到底报了多少件商品？带 catRuleIds 全量查又是多少件？（漏报校正）
  2. 标着"上架"的商品里，有多少件其实兑换窗口早已关闭？（假上架检测）
  3. 真正能兑换的，有几件还需要另付现金？（隐藏现金成本）

用法
----
    export MCD_MCP_TOKEN=你的Token
    python scripts/verify_shelf.py

    # 或直接传参
    python scripts/verify_shelf.py --token 你的Token

Token 申请：https://open.mcd.cn/mcp → 微信扫码登录 → 控制台 → 激活 → 同意服务协议

依赖：仅标准库（urllib），无需 pip install
说明：所有输出均来自麦当劳官方 MCP Server 的真实返回，脚本不做任何数值编造。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime

MCP_URL = 'https://mcp.mcd.cn'

# 商城分类规则 ID。默认不带参数查询时会漏报，必须显式遍历这些分类取全量。
CAT_RULE_IDS = [
    '1>4', '2', '2>8', '2>9',
    '1>6>20', '1>6>21', '1>6>22', '1>6>25', '1>6>34', '1>6>40',
]

# status 字典（实测自 mall-points-products 返回）
STATUS_TEXT = {1: '仓库中', 2: '上架', 3: '售罄', 4: '下架', 5: '预热'}

_opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({'https': 'http://127.0.0.1:9898'}))


# ---------------------------------------------------------------- MCP 基础调用

def rpc(token, method, params, req_id=1, timeout=45):
    """发一次 JSON-RPC 请求并解出 payload。"""
    payload = json.dumps({
        'jsonrpc': '2.0', 'id': req_id, 'method': method, 'params': params
    }).encode('utf-8')
    req = urllib.request.Request(MCP_URL, method='POST', headers={
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
    }, data=payload)
    raw = _opener.open(req, timeout=timeout).read().decode('utf-8', 'replace')
    if 'data:' in raw:
        chunks = [l[5:].strip() for l in raw.split('\n') if l.startswith('data:')]
        return json.loads(chunks[-1])
    return json.loads(raw)


def extract(res):
    """MCP 工具返回体裹了两层：从 text 里抠出原始 JSON。"""
    text = (res.get('result', {}).get('content') or [{}])[0].get('text', '')
    marker = text.find('## Original Response')
    body = text[marker + 19:].strip() if marker >= 0 else text.strip()
    body = re.sub(r'^```json\s*', '', body)
    body = re.sub(r'```\s*$', '', body).strip()
    start = body.find('{')
    if start < 0:
        start = body.find('[')
    if start < 0:
        return None
    body = body[start:]
    opener = body[0]
    closer = '}' if opener == '{' else ']'
    depth = 0
    in_str = False
    escaped = False
    for i, ch in enumerate(body):
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(body[:i + 1])
                except Exception:
                    return None
    return None


def call(token, tool, args, req_id=1):
    """调用一个工具，返回解包后的 data 层。"""
    res = rpc(token, 'tools/call', {'name': tool, 'arguments': args}, req_id)
    if res.get('error'):
        return None
    payload = extract(res)
    if payload is None:
        return None
    # 列表类工具返回 data 是数组，对象类工具返回 data 是对象
    return payload.get('data', payload)


# ---------------------------------------------------------------- 判定helpers

def is_point_item(item):
    """point>0 才是积分结算项。point=0 是需另付现金的活动权益，不等于免费。"""
    return to_num(item.get('point')) > 0


def to_num(value, default=0.0):
    """接口里的数字常以字符串返回，统一转成 float。"""
    if value in (None, ''):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_time(text):
    if not text:
        return None
    try:
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def is_fake_on_shelf(item, now):
    """标着上架(status=2)，但兑换窗口 downTime 已过 → 假上架。"""
    if item.get('status') != 2:
        return False
    end = parse_time(item.get('downTime'))
    return end is not None and end < now


def cash_gap(detail):
    """取该商品 SKU 里需要另付的现金（extTradePrice）。返回最大值。"""
    best = 0.0
    for sku in (detail or {}).get('skuList') or []:
        raw = sku.get('extTradePrice')
        if raw in (None, '', 0, '0'):
            continue
        try:
            best = max(best, float(raw))
        except (TypeError, ValueError):
            continue
    return best


# ---------------------------------------------------------------- 主流程

def audit(token):
    now = datetime.now()

    print('=' * 68)
    print('  麦麦积分真账本 · 货架验真器')
    print('  数据源：麦当劳官方 MCP Server  %s' % MCP_URL)
    print('  验真时刻：%s' % now.strftime('%Y-%m-%d %H:%M:%S'))
    print('=' * 68)

    # --- 1. 默认查询 vs 全量查询 -------------------------------------------
    default_items = call(token, 'mall-points-products', {}, 10) or []
    if not isinstance(default_items, list):
        default_items = []
    default_ids = {x.get('spuId') for x in default_items}
    default_point = [x for x in default_items if is_point_item(x)]

    merged = {}
    for i, rule in enumerate(CAT_RULE_IDS):
        got = call(token, 'mall-points-products', {'catRuleIds': rule}, 100 + i)
        if not isinstance(got, list):
            continue
        for item in got:
            merged[item.get('spuId')] = item
    all_point = [x for x in merged.values() if is_point_item(x)]
    missed = [x for x in all_point if x.get('spuId') not in default_ids]

    print()
    print('【1】漏报校正 —— 默认查询 vs 带 catRuleIds 全量查询')
    print('  默认查询返回      : %3d 件（其中 point>0 的 %d 件）' % (len(default_items), len(default_point)))
    print('  全量查询去重后    : %3d 件（其中 point>0 的 %d 件）' % (len(merged), len(all_point)))
    print('  默认查询漏报     : %3d 件' % len(missed))
    for item in missed:
        print('     · %-34s %s 分' % (item.get('spuName', '?')[:34], item.get('point')))
    if not missed:
        print('     （本次查询未发现漏报）')

    # --- 2. 假上架检测 -------------------------------------------------------
    on_shelf = [x for x in all_point if x.get('status') == 2]
    fake = [x for x in on_shelf if is_fake_on_shelf(x, now)]
    ratio = len(fake) * 100 // max(len(on_shelf), 1)

    print()
    print('【2】假上架检测 —— status=2 但兑换窗口已关闭')
    print('  标为「上架」的积分商品 : %3d 件' % len(on_shelf))
    print('  其中兑换窗口已过期     : %3d 件  (%.0f%%)' % (len(fake), ratio))
    for item in fake:
        print('     · %-32s %5s 分  窗口 %s ~ %s' % (
            item.get('spuName', '?')[:32], item.get('point'),
            (item.get('upTime') or '?')[:16], (item.get('downTime') or '?')[:16]))
    if not fake:
        print('     （本次未发现假上架）')

    # --- 3. 隐藏现金成本 -----------------------------------------------------
    truly = [x for x in on_shelf if not is_fake_on_shelf(x, now)]
    pay_cash, pure = [], []
    for item in truly:
        detail = call(token, 'mall-product-detail', {'spuId': item.get('spuId')},
                      500 + (item.get('spuId') or 0))
        gap = cash_gap(detail)
        (pay_cash if gap > 0 else pure).append((item, gap))

    print()
    print('【3】隐藏现金成本 —— 真正可兑商品里，需另付现金的比例')
    print('  真正可兑商品 : %3d 件' % len(truly))
    print('  其中需另付现金: %3d 件' % len(pay_cash))
    for item, gap in pay_cash:
        print('     · %-32s %5s 分  + 另付 ¥%s' % (
            item.get('spuName', '?')[:32], item.get('point'), gap))
    if not pay_cash:
        print('     （本次未发现隐藏现金成本）')

    # --- 4. 同名多 spuId -----------------------------------------------------
    by_name = defaultdict(list)
    for item in all_point:
        by_name[item.get('spuName')].append(
            (item.get('spuId'), item.get('point')))
    dup = {k: v for k, v in by_name.items() if len(v) > 1}

    print()
    print('【4】同名多 spuId —— 同名商品挂着不同积分，兑换前极易选错')
    print('  命中组数 : %d' % len(dup))
    for name, rows in dup.items():
        print('     · %-34s %s' % (name[:34], rows))

    # --- 5. 可抽次数 ---------------------------------------------------------
    lottery = call(token, 'query-lottery-info', {}, 700) or {}
    if not isinstance(lottery, dict):
        lottery = {}
    draw_point = to_num(lottery.get('drawPoint'))
    account = call(token, 'query-my-account', {}, 701) or {}
    if not isinstance(account, dict):
        account = {}
    available = to_num(account.get('availablePoint'))
    times = int(available // draw_point) if draw_point else 0

    print()
    print('【5】可抽次数 —— 积分唯一的高频出口能回本几次')
    print('  可用积分 : %s 分' % available)
    print('  单次消耗 : %s 分' % draw_point)
    print('  可抽次数 : %s 次' % times)
    print('  活动状态 : %s' % (lottery.get('activityStatusText') or lottery.get('activityName') or '无'))

    # --- 汇总 ----------------------------------------------------------------
    print()
    print('=' * 68)
    print('  真账本汇总')
    print('=' * 68)
    print('  接口报告在架商品        : %d 件' % len(default_items))
    print('  全量在架(去重)          : %d 件' % len(merged))
    print('  其中积分结算项          : %d 件' % len(all_point))
    print('  标为上架但窗口已关闭    : %d 件 (%.0f%%)  ← 假上架' % (len(fake), ratio))
    print('  真正可兑                : %d 件' % len(truly))
    print('  其中需另付现金          : %d 件  ← 隐藏现金成本' % len(pay_cash))
    print('  纯积分可兑              : %d 件' % len(pure))
    print('  积分可抽次数            : %s 次' % times)
    print()
    print('  结论：官方接口报「有 N 件可兑」，实际能真正兑换的是 %d 件。' % len(truly))
    print('=' * 68)

    return {
        'default_count': len(default_items),
        'total_count': len(merged),
        'point_items': len(all_point),
        'on_shelf': len(on_shelf),
        'fake_on_shelf': len(fake),
        'fake_ratio': ratio,
        'truly_redeemable': len(truly),
        'pay_cash': len(pay_cash),
        'pure_points': len(pure),
        'missed_by_default': len(missed),
        'duplicate_names': len(dup),
        'draw_point': draw_point,
        'available_point': available,
        'draw_times': times,
    }


def main():
    parser = argparse.ArgumentParser(
        description='麦当劳积分商城货架验真器（麦麦积分真账本）')
    parser.add_argument('--token', help='麦当劳 MCP Token，默认读环境变量 MCD_MCP_TOKEN')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出汇总结果')
    args = parser.parse_args()

    token = args.token or os.environ.get('MCD_MCP_TOKEN', '').strip()
    if not token:
        print('错误：未找到 Token。请设置环境变量 MCD_MCP_TOKEN 或用 --token 传入。',
              file=sys.stderr)
        print('  Token 申请地址：https://open.mcd.cn/mcp', file=sys.stderr)
        return 2
    if len(token) < 16:
        print('错误：Token 长度异常，请检查是否复制完整。', file=sys.stderr)
        return 2

    try:
        summary = audit(token)
    except Exception as exc:
        print('调用 MCP 失败：%s' % exc, file=sys.stderr)
        print('  请检查网络、Token 有效性，或尝试设置 HTTPS 代理后重试。', file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
