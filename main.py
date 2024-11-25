from osgeo import gdal,ogr
import numpy as np
import Raster
import ZB_hillslope_workflow
import calc_hand
import Extract_Basin_by_Type
import warnings
import argparse
import new_discretize
import util_ZB
import configparser

warnings.filterwarnings("ignore")




# 按间距中的绿色按钮以运行脚本。
if __name__ == '__main__':

    # ***************** Stteper 空间离散化 *****************
    # venu = r'F:\空间离散化\代码示例\example1'
    # stream_file = r'F:\空间离散化\代码示例\example1\Stream100_link.tif'
    # dir_file = r'F:\空间离散化\代码示例\example1\Dir.tif'
    # DEM_file = r'F:\空间离散化\代码示例\example1\DEM.tif'  # DEM
    # Basin_path = r'F:\空间离散化\代码示例\1'  # 子流域shp
    # LU_file=r'F:\空间离散化\代码示例\landuse.tif'
    # Soil_file=r''
    # util_ZB.Check_self_intersect(Basin_path)
    # ZB_hillslope_workflow.Clip_DEM_Dir_Stream_sd_hillslope(Basin_path, dir_file, stream_file, DEM_file, LU_file,venu)
    # calc_hand.main(venu, 6, process=3)
    # new_discretize.merge_HRU(venu)
    # new_discretize.merge_HLU(venu)

    # # 湖泊坡面离散化示例:基于子山坡的空间离散化
    # venu = r'F:\空间离散化\代码示例\example1'
    # dem_file = r'F:\空间离散化\代码示例\example1\DEM.tif'
    # dir_file = r'F:\空间离散化\代码示例\example1\Dir.tif'
    # lake_file = r'F:\空间离散化\代码示例\example1\lakes.tif'
    # stream_file = r'F:\空间离散化\代码示例\example1\Stream100_link.tif'
    # acc_file = r'F:\空间离散化\代码示例\example1\Acc.tif'
    # HAND_file = r'F:\空间离散化\代码示例\example'
    # Basin_path = r'F:\空间离散化\代码示例\example1\1'  # 子流域shp
    # # new_discretize.divide_lake_hillslope(dem_file, dir_file, lake_file, stream_file, acc_file)
    # # util_ZB.Check_self_intersect(Basin_path)
    # ZB_hillslope_workflow.Clip_DEM_Dir_Stream_sd_hillslope(Basin_path, dir_file, stream_file, dem_file, r'', venu)
    # # calc_hand.main(venu, 6, process=3)
    # new_discretize.merge_lake_HRU(venu)

    # 湖泊坡面离散化示例Ammersee:基于子山坡的空间离散化
    # venu = r'F:\空间离散化\代码示例\Ammersee\rundata'
    # dem_file = r'F:\空间离散化\代码示例\Ammersee\rundata\dem.tif'
    # dir_file = r'F:\空间离散化\代码示例\Ammersee\rundata\dir.tif'
    # lake_file = r'F:\空间离散化\代码示例\Ammersee\rundata\AmmerseeLake.tif'
    # stream_file = r'F:\空间离散化\代码示例\Ammersee\rundata\stream60_link.tif'
    # acc_file = r'F:\空间离散化\代码示例\Ammersee\rundata\acc.tif'
    # # HAND_file = r'F:\空间离散化\代码示例\example'
    # Basin_path = r'F:\空间离散化\代码示例\Ammersee\rundata\1'  # 子流域shp
    # # new_discretize.divide_lake_hillslope(dem_file, dir_file, lake_file, stream_file, acc_file)
    # # util_ZB.Check_self_intersect(Basin_path)
    # # ZB_hillslope_workflow.Clip_DEM_Dir_Stream_sd_hillslope(Basin_path, dir_file, stream_file, dem_file, r'', venu)
    # # calc_hand.main(venu, 6, process=3)
    # new_discretize.merge_lake_HRU(venu)

    # 湖泊坡面离散化示例Amper:基于子山坡的空间离散化
    venu = r'F:\空间离散化\小流域测试\Amper\rundata'
    dem_file = r'F:\空间离散化\小流域测试\Amper\rundata\dem.tif'
    dir_file = r'F:\空间离散化\小流域测试\Amper\rundata\dir.tif'
    lake_file = r'F:\空间离散化\小流域测试\Amper\rundata\lakes.tif'
    stream_file = r'F:\空间离散化\小流域测试\Amper\rundata\stream61.tif'
    acc_file = r'F:\空间离散化\小流域测试\Amper\rundata\acc.tif'
    # HAND_file = r'F:\空间离散化\代码示例\example'
    Basin_path = r'F:\空间离散化\小流域测试\Amper\rundata\1'  # 子流域shp
    new_discretize.divide_lake_hillslope(dem_file, dir_file, lake_file, stream_file, acc_file)
    # util_ZB.Check_self_intersect(Basin_path)
    # ZB_hillslope_workflow.Clip_DEM_Dir_Stream_sd_hillslope(Basin_path, dir_file, stream_file, dem_file, r'', venu)
    # calc_hand.main(venu, 6, process=3)
    new_discretize.merge_lake_HRU(venu)