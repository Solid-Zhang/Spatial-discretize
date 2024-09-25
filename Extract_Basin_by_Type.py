from osgeo import gdal,ogr,osr
import numpy as np
import os.path
def Write_Field(layer,Name,Type):
    """
    写入字段，默认Width=24，Precision=6
    :param layer:shp文件名
    :param Name: 字段名称
    :param Type: 字段类型
    :return:
    """
    field_name = ogr.FieldDefn(Name, Type)
    if Type==ogr.OFTReal:
        field_name.SetWidth(24)
        field_name.SetPrecision(6)
    layer.CreateField(field_name)

def Creat_Shp(file_path):
    """
    创建图层，字段名可根据用户需求改动，
    :param file_path: 路径
    :return:
    """
    driver=ogr.GetDriverByName('ESRI Shapefile')
    datasource=driver.CreateDataSource(file_path)
    srs = osr.SpatialReference()
    # 坐标系统
    srs.ImportFromEPSG(4326)
    layer = datasource.CreateLayer("volcanoes", srs, ogr.wkbPolygon)

    # Add the fields we're interested in
    # field_name = ogr.FieldDefn("Pfaf_ID", ogr.OFTReal)
    # field_name.SetWidth(24)
    # layer.CreateField(field_name)
    Write_Field(layer, 'Basin_ID', ogr.OFTReal)
    Write_Field(layer,'Down_ID',ogr.OFTReal)
    Write_Field(layer, 'Type', ogr.OFTReal)
    Write_Field(layer, 'Area', ogr.OFTReal)
    Write_Field(layer, 'Hylak_id', ogr.OFTReal)

    Write_Field(layer, 'Endor', ogr.OFSTInt16)
    # Write_Field(layer, 'Island_Num', ogr.OFSTInt16)
    Write_Field(layer, 'Outlet_lon', ogr.OFTReal)
    Write_Field(layer, 'Outlet_lat', ogr.OFTReal)
    # Write_Field(layer, 'Inlet_lon', ogr.OFTReal)
    # Write_Field(layer, 'Inlet_lat', ogr.OFTReal)
    Write_Field(layer, 'Shape_Leng', ogr.OFTReal)
    Write_Field(layer, 'Shape_Area', ogr.OFTReal)

def Extract_Basin_by_Type(Basin_file,venu):
    datasource=ogr.Open(Basin_file)
    layer=datasource.GetLayer()
    num=layer.GetFeatureCount()
    # print(layer,num)


    Type1_dir=os.path.join(venu,'1')
    Type2_dir = os.path.join(venu, '2')
    Type3_dir = os.path.join(venu, '3')
    if not os.path.exists(Type1_dir):
        os.mkdir(Type1_dir)
    if not os.path.exists(Type2_dir):
        os.mkdir(Type2_dir)
    if not os.path.exists(Type3_dir):
        os.mkdir(Type3_dir)



    print("子流域文件正在写入...")
    for j in layer:
        # 创建new_shape
        Type=str(j.GetField("Type"))
        # print(Type)
        ID=str(int(j.GetField("Basin_ID")))

        path=os.path.join(venu,Type,ID+'.shp')
        Creat_Shp(path)
        C = ogr.Open(path, 1)
        L = C.GetLayer()

        # print(path)
        # 获取形状
        feature = ogr.Feature(L.GetLayerDefn())
        # 设置字段
        feature.SetField("Basin_ID", j.GetField("Basin_ID"))
        feature.SetField("Down_ID", j.GetField("Down_ID"))
        feature.SetField("Type", j.GetField("Type"))
        feature.SetField("Area", j.GetField("Area"))
        feature.SetField("Endor", j.GetField("Endor"))
        feature.SetField('Hylak_id',j.GetField('Hylak_id'))

        feature.SetField("Outlet_lon", j.GetField("Outlet_lon"))
        feature.SetField("Outlet_lat", j.GetField("Outlet_lat"))

        feature.SetField("Shape_Leng", j.GetField("Shape_Leng"))
        feature.SetField("Shape_Area", j.GetField("Shape_Area"))
        # 设置基准面
        feature.SetGeometry(j.GetGeometryRef())
        # 创建
        L.CreateFeature(feature)

    print('\n***************************************************************')
    print('|                                                              |')
    print('|             完成子流域的提取。                                   |')
    print('|                                                              |')
    print('***************************************************************')

if __name__=='__main__':
    # Basin_file=r'E:\青藏高原东部河流输出碳\DATA\LongRiver_simulation\LakeBasins_LongRiver\Level12.shp'
    # venu = r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Level12'
    # Extract_Basin_by_Type(Basin_file,venu)
    pass