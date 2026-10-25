#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影子价格敏感度验证器
=====================

积分商城里，每一分的"真实价值"取决于你把哪些商品算进兑换池。

麦当劳官方接口的 `mall-points-products` 返回的商品列表里，`status` 字段标注为
`2`（上架）的商品，有相当一部分其 `downTime`（兑换窗口结束时间）早已过期，
但接口的状态字段不会同步更新。

于是"积分商城里最优兑换效率"这个数字会随口径而变：

  宽松口径（信任 status）      —— 池子里混入已过期的商品
  严格口径（额外要求 downTime 未过期）

本脚本用**同一批真实 MCP 数据**分别算两种口径，直观展示差额。
这不是批评任何人的口径选择，而是让使用这个数字的人知道它取决于什么。

用法
----
    export MCD_MCP_TOKEN=你的Token
    python scripts/verify_shadow_price.py

依赖：仅 Python 标准库
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

MCP_URL = 'https://mcp.mcd.cn'

# 积分商城分类规则（逗号分隔字符串，不是数组）。不遍历会漏报。
CAT_RULE_IDS = [
    '1>4', '2', '2>8', '2>9',
    '1>6>20', '1>6>21', '1>6>22', '1>6>25', '1>6>34', '1>6>40',
]

_opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({'https': 'http://127.0.0.1:9898'}))


# ---------------------------------------------------------------- MCP 调用

def rpc(token, method, params, req_id=1, timeout=45):
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
    """工具返回体裹了两层：从 text 里抠出原始 JSON。"""
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
    res = rpc(token, 'tools/call', {'name': tool, 'arguments': args}, req_id)
    if res.get('error'):
        return None
    payload = extract(res)
    if payload is None:
        return None
    return payload.get('data', payload)


# ---------------------------------------------------------------- 计算helpers

def to_num(value, default=0.0):
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


def face_value(item):
    """从商品标题里取「XX元」面值。没有明确面值的算不出来。"""
    match = re.search(r'(\d+(?:\.\d+)?)\s*元', item.get('spuName') or '')
    return float(match.group(1)) if match else None


def efficiency(item):
    """每积分换回多少元。返回 (效率, 面值, 积分) 或 None。"""
    face = face_value(item)
    points = to_num(item.get('point'))
    if face is None or points <= 0:
        return None
    return face / points, face, points


def rank_pool(pool, label):
    """算出池子里的效率分布，返回排序后的列表。"""
    scored = []
    for item in pool:
        result = efficiency(item)
        if result and result[0] > 0:
            scored.append((result[0], item.get('spuName'), result[2]))
    scored.sort(reverse=True)
    if not scored:
        print('  %-26s （无可计算标的）' % label)
        return None
    top, bottom = scored[0], scored[-1]
    print('  %-26s 最优 = %.4f 元/积分   %s（%d 分）'
          % (label, top[0], top[1][:32], top[2]))
    print('  %-26s 最差 = %.4f 元/积分' % ('', bottom[0]))
    print('  %-26s 最高/最低 = %.1f 倍' % ('', top[0] / bottom[0]))
    return scored


# ---------------------------------------------------------------- 主流程

def verify(token):
    now = datetime.now()
    print('=' * 74)
    print('  积分商城「影子价格」口径敏感度验证')
    print('  数据源：%s  ·  %s' % (MCP_URL, now.strftime('%Y-%m-%d %H:%M:%S')))
    print('=' * 74)

    merged = {}
    for i, rule in enumerate(CAT_RULE_IDS):
        got = call(token, 'mall-points-products', {'catRuleIds': rule}, 100 + i)
        if isinstance(got, list):
            for item in got:
                merged[item.get('spuId')] = item

    items = [x for x in merged.values() if to_num(x.get('point')) > 0]
    on_shelf = [x for x in items if x.get('status') == 2]
    strict = []
    for item in on_shelf:
        end = parse_time(item.get('downTime'))
        if end is None or end >= now:
            strict.append(item)

    print()
    print('【池子 A】信任 status 字段（status=2 即认为可兑）')
    loose = rank_pool(on_shelf, 'A. status=2 全部')

    print()
    print('【池子 B】额外要求 downTime 未过期')
    tight = rank_pool(strict, 'B. 过滤过期窗口')

    print()
    print('=' * 74)
    print('  结论')
    print('=' * 74)
    print('  宽松口径纳入 %d 件，严格口径只剩 %d 件。' % (len(on_shelf), len(strict)))
    if loose and tight:
        print('  最优效率：%.4f → %.4f 元/积分（口径不同，结论相差 %.1f%%）'
              % (loose[0][0], tight[0][0],
                 abs(loose[0][0] - tight[0][0]) / tight[0][0] * 100))
        print('  价值极差：%.1f 倍 → %.1f 倍'
              % (loose[0][0] / loose[-1][0], tight[0][0] / tight[-1][0]))
    print()
    print('  这不是"哪个口径对"，而是"这个数字取决于什么"：')
    print('  用它做「花积分是否划算」的判断时，必须先说清用的是哪个池子。')
    print('=' * 74)

    return {
        'pool_loose': len(on_shelf),
        'pool_strict': len(strict),
        'best_loose': loose[0][0] if loose else None,
        'best_strict': tight[0][0] if tight else None,
        'spread_loose': (loose[0][0] / loose[-1][0]) if loose else None,
        'spread_strict': (tight[0][0] / tight[-1][0]) if tight else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description='积分商城影子价格口径敏感度验证（麦麦积分真账本）')
    parser.add_argument('--token', help='麦当劳 MCP Token，默认读环境变量 MCD_MCP_TOKEN')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出汇总')
    args = parser.parse_args()

    token = args.token or os.environ.get('MCD_MCP_TOKEN', '').strip()
    if not token:
        print('错误：未找到 Token。请设置 MCD_MCP_TOKEN 或用 --token 传入。', file=sys.stderr)
        print('  Token 申请地址：https://open.mcd.cn/mcp', file=sys.stderr)
        return 2

    try:
        summary = verify(token)
    except Exception as exc:
        print('调用 MCP 失败：%s' % exc, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
