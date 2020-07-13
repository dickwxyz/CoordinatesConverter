# CoordinatesConverter.py


## 功能
此程序实现了大地坐标系、火星坐标系、百度经纬度坐标系、百度墨卡托米制坐标系之间的互转，此外可以计算两点之间的球面距离。  

1. 大地坐标系：wgs84，目前广泛使用的GPS全球卫星定位系统使用的坐标系。ArcGIS中`GCS_WGS_1984`使用此坐标系，epsg:4326。
2. 火星坐标系：gcj02，是由中国国家测绘局制订的地理信息系统的坐标系统，由WGS84坐标系经加密后的坐标系。`高德地图`、`Excel Power Map`使用此坐标系。  
3. 百度经纬度坐标系：bd09ll，在GCJ02坐标系基础上再次加密，bd09ll表示百度经纬度坐标，bd09mc表示百度墨卡托米制坐标。`百度地图API`使用此坐标系。  
4. 百度墨卡托米制坐标系：bd09mc。`百度地图后台抓取`使用此坐标系。  

**主要函数**：  
1.  wgs84togcj02(lon, lat)  
2. gcj02towgs84(lon, lat)  
3. gcj02tobd09ll(lon, lat)    
4. bd09lltogcj02(lon, lat)  
5. wgs84tobd09ll(lon, lat)    
6. bd09lltowgs84(lon, lat)  
7. bd09mctobd09ll(lon, lat)  
8. CalDistance(lon1, lat1, lon2, lat2)  

**补充**：  
墨卡托坐标系`WGS_1984_Web_Mercator_Auxiliary_Sphere`，epsg:3857。  
安装`geopandas`包，用法：

```python
import geopandas as gpd
shp = gpd.read_file(path)
shp.crs = {'init':'epsg:4326'} 
shp = shp.to_crs({'init':'epsg:3857'})
```

**参考资料**：[坐标系说明](https://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-geocoding)
## 用法
将`CoordinatesConverter.py`文件与jupyter文件放在同一目录下。代码示例如下：  

```python
import CoordinatesConverter as cc  
lon, lat = cc.bd09lltowgs84(bd_lon, bd_lat)
```


