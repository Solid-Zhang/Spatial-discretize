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
    venu = r'F:\空间离散化\代码示例'
    stream_file = r'F:\空间离散化\代码示例\basin_Stream.tif'
    dir_file = r'F:\空间离散化\代码示例\basin_dir.tif'
    DEM_file = r'F:\空间离散化\代码示例\basin_elv.tif'  # DEM
    Basin_path = r'F:\空间离散化\代码示例\1'  # 子流域shp
    LU_file=r'F:\空间离散化\代码示例\landuse.tif'
    Soil_file=r''
    # util_ZB.Check_self_intersect(Basin_path)
    # ZB_hillslope_workflow.Clip_DEM_Dir_Stream_sd_hillslope(Basin_path, dir_file, stream_file, DEM_file, LU_file,venu)
    calc_hand.main(venu, 6, process=3)
    # new_discretize.merge_HRU(venu)
    # new_discretize.merge_HLU(venu)
