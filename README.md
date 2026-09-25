# CoordinatesConverter.py


## 功能
此程序实现了大地坐标系、火星坐标系、百度经纬度坐标系、百度墨卡托米制坐标系之间的互转，此外可以计算两点之间的球面距离，并提供时间戳与字符串时刻的互转。  

1. 大地坐标系：wgs84，目前广泛使用的GPS全球卫星定位系统使用的坐标系。ArcGIS中`GCS_WGS_1984`使用此坐标系，epsg:4326。
2. 火星坐标系：gcj02，是由中国国家测绘局制订的地理信息系统的坐标系统，由WGS84坐标系经加密后的坐标系。`高德地图`、`Excel Power Map`使用此坐标系。  
3. 百度经纬度坐标系：bd09ll，在GCJ02坐标系基础上再次加密。`百度地图API`使用此坐标系。  
4. 百度墨卡托米制坐标系：bd09mc。`百度地图后台抓取`使用此坐标系。  

## 主要函数

**经纬度坐标系互转**：  
1. wgs84togcj02(lon, lat)  
2. gcj02towgs84(lon, lat)  
3. gcj02tobd09ll(lon, lat)    
4. bd09lltogcj02(lon, lat)  
5. wgs84tobd09ll(lon, lat)    
6. bd09lltowgs84(lon, lat)  

**百度墨卡托米制坐标系（bd09mc）互转**：  
7. bd09mctobd09ll(x, y)  
8. bd09lltobd09mc(lon, lat)  
9. wgs84tobd09mc(lon, lat)  
10. bd09mctowgs84(x, y)  

**距离计算**：  
11. CalDistance(lon1, lat1, lon2, lat2)，返回两点球面距离，单位千米  

**时间戳与字符串时刻互转**：  
12. `str_to_timestamp(string)`，入参支持 `'20230807090303'`、`'2023/08/07 09:03:03'`、`'2023-08-07 09:03:03'` 三种写法  
13. `timestamp_to_str(timestamp)`，输出格式 `'%Y/%m/%d %H:%M:%S'`  

内部函数：`transformlat`、`transformlng`、`out_of_china`，供上述函数调用，一般无需直接使用。

## 已知限制

1. `bd09mctobd09ll` 在 `y <= 0`（赤道及南半球）时不会命中任何波段，抛 `UnboundLocalError`。bd09mc 仅在中国境内有意义，常规使用不会触及。  
2. `bd09lltobd09mc` 在 `|lat| >= 75` 时输出失真（系数表首行数值异常）。中国境内最高纬约 53.5°N，实际用不到。  
3. `wgs84tobd09ll` 在境外不会短路，仍会叠加百度偏移（`gcj02tobd09ll` 本身不含境内判断）。  

详见 [测试报告.md](./测试报告.md)。

## 用法
将`CoordinatesConverter.py`与调用它的文件放在同一目录下。代码示例如下：  

```python
import CoordinatesConverter as cc  
lon, lat = cc.bd09lltowgs84(bd_lon, bd_lat)
```

## 测试

自检脚本 `test.py`，仅依赖标准库，无需安装任何第三方包：

```bash
python3 -B test.py
```

`-B` 用于不生成 `__pycache__`（本仓库把 `.pyc` 纳入了 git）。全部通过退出码为 `0`，有失败为 `1`，可直接用于 CI 步骤。当前 32 项用例全部通过，详见 [测试报告.md](./测试报告.md)。

测试函数命名为 `test_*` 且只做断言、无副作用，装了 pytest 后也可直接收集运行：

```bash
pytest test.py
```

**补充**：  
墨卡托坐标系`WGS_1984_Web_Mercator_Auxiliary_Sphere`，epsg:3857。  
安装`geopandas`包，用法：

```python
import geopandas as gpd
shp = gpd.read_file(path)
shp.crs = {'init':'epsg:4326'} 
shp = shp.to_crs({'init':'epsg:3857'})
```

**参考资料**：[坐标系说明](https://lbsyun.baidu.com/index.php?title=coordinate)
