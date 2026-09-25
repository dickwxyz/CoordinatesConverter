# -*- coding: utf-8 -*-
"""
CoordinatesConverter.py 独立自检测试

运行：
    python3 -B test.py

    -B 是为了不生成 __pycache__（本项目把 .pyc 纳入了 git）。
    全通过退出码 0，有失败退出码 1。

测试函数一律命名为 test_* 且只做断言、无副作用，因此将来装了 pytest
也能直接收集运行：
    pytest test.py

预期值不取自 Test.ipynb，来自三条独立来源：
    1. 往返闭合      —— 自洽性，不需要外部数据
    2. 球面几何常识  —— CalDistance 的解析解
    3. 百度发布的东方明珠实测坐标 —— 外部锚点，与 image/ 下截图同一 POI

已知限制（本文件不断言，仅在此记录，避免把缺陷固化成期望行为）：
    * bd09mctobd09ll 在 y1 <= 0（赤道及南半球）时不命中任何波段，
      cF 未绑定，抛 UnboundLocalError
    * bd09lltobd09mc 在 |lat| >= 75 时命中 LL2MC[0] 的畸变系数，输出完全
      失真；中国境内最高纬约 53.5°N，实际用不到，故波段采样上界取 61°
    * wgs84tobd09ll 在境外不会短路（gcj02tobd09ll 本身没有 out_of_china
      检查），境外点仍会被叠加百度偏移，属既有行为
"""
import math
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import CoordinatesConverter as cc


# ---------------------------------------------------------------- 测试登记

_TESTS = []  # [(组名, 函数名, 函数)]


def case(group_name):
    """把被装饰的函数登记进指定分组。

    名字不能以 test 开头，否则 pytest 会把这个装饰器本身当成测试函数收集，
    再因为缺 group_name 参数而报 fixture 错误。
    """
    def deco(fn):
        _TESTS.append((group_name, fn.__name__, fn))
        return fn
    return deco


# ---------------------------------------------------------------- 工具函数

def close(a, b, tol):
    return abs(a - b) <= tol


def close_pt(p, q, tol):
    return close(p[0], q[0], tol) and close(p[1], q[1], tol)


def meters(p, q):
    """两点球面距离，米。CalDistance 返回的是千米。"""
    return cc.CalDistance(p[0], p[1], q[0], q[1]) * 1000.0


# 覆盖不同纬度带与经度带的境内样本，用于往返与波段测试
CITIES = [
    ('北京',     116.397, 39.909),
    ('广州',     113.264, 23.129),
    ('哈尔滨',   126.535, 45.803),
    ('三亚',     109.508, 18.247),
    ('拉萨',      91.140, 29.645),
    ('乌鲁木齐',  87.617, 43.793),
    ('上海',     121.506, 31.245),
    ('喀什',      75.990, 39.470),
    ('漠河',     122.530, 53.470),
]

# 公开 API，改动或误删会立刻暴露
PUBLIC = [
    'str_to_timestamp', 'timestamp_to_str',
    'wgs84togcj02', 'gcj02towgs84', 'transformlat', 'transformlng',
    'out_of_china', 'gcj02tobd09ll', 'bd09lltogcj02',
    'wgs84tobd09ll', 'bd09lltowgs84',
    'bd09mctobd09ll', 'bd09lltobd09mc', 'wgs84tobd09mc', 'bd09mctowgs84',
    'CalDistance',
]


# ================================================================ 1. 模块结构

@case('1. 模块结构')
def test_all_public_functions_exist():
    missing = [n for n in PUBLIC if not callable(getattr(cc, n, None))]
    assert not missing, '缺少或不可调用的函数: %s' % missing


@case('1. 模块结构')
def test_constants_present():
    for name, expected in [('MCBAND', 6), ('LLBAND', 6), ('MC2LL', 6), ('LL2MC', 6)]:
        table = getattr(cc, name, None)
        assert table is not None, '缺少常量 %s' % name
        assert len(table) == expected, '%s 应有 %d 行，实际 %d' % (name, expected, len(table))


# ============================================================== 2. 时间函数

@case('2. 时间函数')
def test_compact_and_dash_agree():
    """紧凑格式与横杠格式应解析为同一时刻。"""
    compact = cc.str_to_timestamp('20230807090303')
    dash = cc.str_to_timestamp('2023-08-07 09:03:03')
    assert compact == dash, '同一时刻两种写法解析结果不一致: %r != %r' % (compact, dash)


@case('2. 时间函数')
def test_slash_format_parses():
    """str_to_timestamp 的 docstring 承诺支持 '2023/08/07 09:03:03'。"""
    expected = cc.str_to_timestamp('20230807090303')
    got = cc.str_to_timestamp('2023/08/07 09:03:03')
    assert got == expected, (
        "斜杠格式 '2023/08/07 09:03:03' 解析结果 %r 与紧凑格式 %r 不符" % (got, expected))


@case('2. 时间函数')
def test_timestamp_to_str_output_format():
    """钉住输出格式为 %Y/%m/%d %H:%M:%S，防止无意漂移。"""
    out = cc.timestamp_to_str(cc.str_to_timestamp('20230807090303'))
    assert out == '2023/08/07 09:03:03', 'timestamp_to_str 输出为 %r' % out


@case('2. 时间函数')
def test_roundtrip_ts_str_ts():
    """输出端与解析端的格式协议必须一致，否则往返会断。"""
    ts = cc.str_to_timestamp('20230807090303')
    text = cc.timestamp_to_str(ts)
    back = cc.str_to_timestamp(text)
    assert back == ts, 'ts -> str -> ts 往返失败: %r -> %r -> %r' % (ts, text, back)


@case('2. 时间函数')
def test_roundtrip_str_ts_str():
    """str -> ts -> str 方向此前是好的，不能被弄坏。"""
    text = '20230807090303'
    assert cc.timestamp_to_str(cc.str_to_timestamp(text)) == '2023/08/07 09:03:03'


@case('2. 时间函数')
def test_timestamps_mutually_consistent():
    """str 与 ts 互转都走本地时区，故只断言往返恒等，不硬编码绝对时间戳，
    这样在任何 TZ 下都成立。"""
    for text in ['20230807090303', '19990101000000', '20301231235959']:
        assert cc.timestamp_to_str(cc.str_to_timestamp(text)) == (
            '%s/%s/%s %s:%s:%s' % (text[0:4], text[4:6], text[6:8], text[8:10], text[10:12], text[12:14]))


# ============================================================ 3. 境内境外判定

@case('3. 境内境外判定')
def test_out_of_china_classification():
    inside = [('北京', 116.397, 39.909), ('上海', 121.506, 31.245),
              ('拉萨', 91.140, 29.645), ('喀什', 75.990, 39.470)]
    outside = [('东京', 139.767, 35.681), ('纽约', -74.006, 40.713),
               ('经度下限外', 72.0, 30.0), ('经度上限外', 137.9, 30.0),
               ('纬度下限外', 110.0, 0.5), ('纬度上限外', 110.0, 55.9)]
    for name, lng, lat in inside:
        assert cc.out_of_china(lng, lat) is False, '%s 应判为境内' % name
    for name, lng, lat in outside:
        assert cc.out_of_china(lng, lat) is True, '%s 应判为境外' % name


@case('3. 境内境外判定')
def test_overseas_is_identity_for_gcj02():
    """境外点经 wgs84togcj02 / gcj02towgs84 必须原样返回（两者都有短路）。"""
    for name, lng, lat in [('东京', 139.767, 35.681), ('纽约', -74.006, 40.713)]:
        assert close_pt(cc.wgs84togcj02(lng, lat), (lng, lat), 1e-12), \
            '%s wgs84togcj02 未短路' % name
        assert close_pt(cc.gcj02towgs84(lng, lat), (lng, lat), 1e-12), \
            '%s gcj02towgs84 未短路' % name


# ============================================================== 4. 偏移量级

@case('4. 偏移量级')
def test_gcj02_offset_magnitude():
    """中国境内 GCJ-02 相对 WGS-84 的偏移在数百米量级。
    实测区间 255 ~ 622 m，取 100 ~ 1000 m。"""
    for name, lng, lat in CITIES:
        d = meters((lng, lat), cc.wgs84togcj02(lng, lat))
        assert 100.0 <= d <= 1000.0, '%s gcj02-wgs84 偏移 %.1f m 超出预期区间' % (name, d)


@case('4. 偏移量级')
def test_bd09ll_offset_magnitude():
    """BD09LL 相对 GCJ-02 的偏移在近千米量级。
    实测区间 809 ~ 960 m，取 500 ~ 1200 m。"""
    for name, lng, lat in CITIES:
        gcj = cc.wgs84togcj02(lng, lat)
        bd = cc.gcj02tobd09ll(*gcj)
        d = meters(gcj, bd)
        assert 500.0 <= d <= 1200.0, '%s bd09ll-gcj02 偏移 %.1f m 超出预期区间' % (name, d)


# ============================================================== 5. 往返闭合

ROUNDTRIPS = [
    ('bd09ll -> bd09mc -> bd09ll', cc.bd09lltobd09mc, cc.bd09mctobd09ll, 1.0),
    ('bd09ll -> gcj02 -> bd09ll',  cc.bd09lltogcj02,  cc.gcj02tobd09ll,  1.0),
    ('wgs84 -> bd09ll -> wgs84',   cc.wgs84tobd09ll,  cc.bd09lltowgs84,  10.0),
    ('wgs84 -> gcj02 -> wgs84',    cc.wgs84togcj02,   cc.gcj02towgs84,   10.0),
    ('wgs84 -> bd09mc -> wgs84',   cc.wgs84tobd09mc,  cc.bd09mctowgs84,  10.0),
]


def _make_roundtrip(label, forward, inverse, tol_m):
    def fn():
        # 前两条的米级残差来自 bd09mc 多项式拟合，后三条来自 gcj02 那对
        # 近似互逆公式，均为固有特性，阈值已按实测留足余量
        for name, lng, lat in CITIES:
            back = inverse(*forward(lng, lat))
            d = meters((lng, lat), back)
            assert d <= tol_m, '%s 在 %s 往返误差 %.4f m 超过 %.1f m' % (label, name, d, tol_m)
    fn.__name__ = 'test_roundtrip_' + label.replace(' ', '').replace('->', '_to_')
    return fn


for _label, _fwd, _inv, _tol in ROUNDTRIPS:
    _fn = _make_roundtrip(_label, _fwd, _inv, _tol)
    case('5. 往返闭合')(_fn)
    # 同时绑定到模块级名字，否则 pytest 按属性名收集时会漏掉这几个
    globals()[_fn.__name__] = _fn


# ============================================================ 6. 组合一致性

@case('6. 组合一致性')
def test_wgs84tobd09ll_matches_composition():
    for name, lng, lat in CITIES:
        got = cc.wgs84tobd09ll(lng, lat)
        want = cc.gcj02tobd09ll(*cc.wgs84togcj02(lng, lat))
        assert close_pt(got, want, 1e-12), '%s wgs84tobd09ll 与实际分步结果不符' % name


@case('6. 组合一致性')
def test_bd09lltowgs84_matches_composition():
    for name, lng, lat in CITIES:
        bd = cc.wgs84tobd09ll(lng, lat)
        got = cc.bd09lltowgs84(*bd)
        want = cc.gcj02towgs84(*cc.bd09lltogcj02(*bd))
        assert close_pt(got, want, 1e-12), '%s bd09lltowgs84 与实际分步结果不符' % name


@case('6. 组合一致性')
def test_wgs84tobd09mc_matches_composition():
    for name, lng, lat in CITIES:
        got = cc.wgs84tobd09mc(lng, lat)
        want = cc.bd09lltobd09mc(*cc.wgs84tobd09ll(lng, lat))
        assert close_pt(got, want, 1e-9), '%s wgs84tobd09mc 与实际分步结果不符' % name


@case('6. 组合一致性')
def test_bd09mctowgs84_matches_composition():
    for name, lng, lat in CITIES:
        mc = cc.wgs84tobd09mc(lng, lat)
        got = cc.bd09mctowgs84(*mc)
        want = cc.bd09lltowgs84(*cc.bd09mctobd09ll(*mc))
        assert close_pt(got, want, 1e-9), '%s bd09mctowgs84 与实际分步结果不符' % name


# ======================================================== 7. 百度墨卡托外部锚点

# 百度自身发布的东方明珠实测坐标，与 image/ 下截图同一 POI
POI_MC = (13526175.38, 3642294.77)
POI_LL = (121.50637870800159, 31.245413754402072)


@case('7. 外部锚点')
def test_bd09mc_to_bd09ll_against_baidu():
    got = cc.bd09mctobd09ll(*POI_MC)
    assert close_pt(got, POI_LL, 1e-9), 'bd09mctobd09ll 结果 %r 与百度实测 %r 不符' % (got, POI_LL)


@case('7. 外部锚点')
def test_bd09ll_to_bd09mc_against_baidu():
    """锚点只有两位小数，米级以内的差属截断误差。"""
    got = cc.bd09lltobd09mc(*POI_LL)
    assert close_pt(got, POI_MC, 1.0), 'bd09lltobd09mc 结果 %r 与百度实测 %r 不符' % (got, POI_MC)


@case('7. 外部锚点')
def test_anchor_roundtrip_through_wgs84():
    """锚点绕一圈 wgs84 回来，仍应落回原地（容许 gcj02 近似互逆的米级残差）。"""
    wgs = cc.bd09lltowgs84(*POI_LL)
    back = cc.wgs84tobd09ll(*wgs)
    assert meters(POI_LL, back) <= 10.0, '锚点绕 wgs84 往返误差 %.4f m' % meters(POI_LL, back)


# =============================================================== 8. 距离计算

@case('8. 距离计算')
def test_one_degree_latitude_at_equator():
    """沿经线 1 度 = 2*pi*R/360，R 取 6378.137 km，是精确解析解。"""
    expected = 2 * math.pi * 6378.137 / 360
    got = cc.CalDistance(0.0, 0.0, 0.0, 1.0)
    assert close(got, expected, 0.01), '1 度纬度 @赤道 得 %.6f km，解析值 %.6f km' % (got, expected)


@case('8. 距离计算')
def test_one_degree_longitude_at_equator():
    expected = 2 * math.pi * 6378.137 / 360
    got = cc.CalDistance(0.0, 0.0, 1.0, 0.0)
    assert close(got, expected, 0.01), '1 度经度 @赤道 得 %.6f km，解析值 %.6f km' % (got, expected)


@case('8. 距离计算')
def test_one_degree_longitude_shrinks_with_latitude():
    """高纬度处 1 度经度应约等于赤道值乘 cos(lat)。

    注意这里比较的是大圆距离与同纬度纬圈弧长，两者天然略有差别：实测
    95.17811 km vs 解析 95.17843 km，差 0.32 m，故容差取 0.05 km。
    """
    lat = 31.24
    expected = 2 * math.pi * 6378.137 / 360 * math.cos(math.radians(lat))
    got = cc.CalDistance(0.0, lat, 1.0, lat)
    assert close(got, expected, 0.05), '1 度经度 @%.2f 得 %.5f km，解析值 %.5f km' % (lat, got, expected)


@case('8. 距离计算')
def test_distance_is_symmetric():
    a, b = (121.5, 31.2), (116.4, 39.9)
    assert close(cc.CalDistance(*a, *b), cc.CalDistance(*b, *a), 1e-12), '距离不对称'


@case('8. 距离计算')
def test_zero_distance():
    assert close(cc.CalDistance(121.5, 31.2, 121.5, 31.2), 0.0, 1e-12)


@case('8. 距离计算')
def test_shanghai_beijing_distance():
    """上海到北京球面直线距离实测 1069.0 km，取 1000 ~ 1150 km。"""
    d = cc.CalDistance(121.49533505039834, 31.241787725896685, 116.3975, 39.9087)
    assert 1000.0 <= d <= 1150.0, '上海到北京得 %.2f km' % d


# =========================================================== 9. 墨卡托波段连续性

@case('9. 墨卡托波段连续性')
def test_band_transitions_are_continuous():
    """LLBAND = [75, 60, 45, 30, 15, 0]，在各波段边界跨越时输出必须连续。
    实测 0.001 度步长的最大相邻跳变 236.9 m，出现在 60 度边界，取 400 m。"""
    lat = 14.0
    prev = None
    while lat <= 61.0:
        y = cc.bd09lltobd09mc(116.4, lat)[1]
        if prev is not None:
            step = y - prev
            assert step > 0, 'mc_y 在 lat=%.3f 处非单调递增（步长 %.3f）' % (lat, step)
            assert step <= 400.0, 'lat=%.3f 处相邻跳变 %.1f m 过大，疑似波段切换断裂' % (lat, step)
        prev = y
        lat = round(lat + 0.001, 4)


@case('9. 墨卡托波段连续性')
def test_bd09lltobd09mc_handles_equator():
    """正向函数在 y=0 时应命中最后一行（判断用 >=），不应崩溃。"""
    x, y = cc.bd09lltobd09mc(116.4, 0.0)
    assert close(y, 0.0, 1.0), '赤道处 mc_y 得 %r，应接近 0' % y
    assert x > 0, '赤道处 mc_x 得 %r，应为正' % x


# ==================================================================== 运行器

def main():
    results = []  # [(组名, 函数名, 是否通过, 详情)]
    for group_name, fn_name, fn in _TESTS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - 测试运行器需要兜住一切
            detail = traceback.format_exc().strip().splitlines()[-1]
            if not isinstance(exc, AssertionError):
                detail = '%s: %s' % (type(exc).__name__, exc)
            results.append((group_name, fn_name, False, detail))
        else:
            results.append((group_name, fn_name, True, ''))

    print('CoordinatesConverter.py 自检')
    print('=' * 68)
    current = None
    for group_name, fn_name, ok, detail in results:
        if group_name != current:
            current = group_name
            print('\n[%s]' % group_name)
        print('  %s  %s' % ('PASS' if ok else 'FAIL', fn_name))

    n_pass = sum(1 for r in results if r[2])
    n_fail = len(results) - n_pass
    print('\n' + '-' * 68)
    print('通过 %d / %d，失败 %d' % (n_pass, len(results), n_fail))

    if n_fail:
        print('\n失败明细：')
        for group_name, fn_name, ok, detail in results:
            if not ok:
                print('  [%s] %s\n      %s' % (group_name, fn_name, detail))

    return 1 if n_fail else 0


if __name__ == '__main__':
    sys.exit(main())
