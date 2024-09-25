from osgeo import gdal,ogr,osr
import numpy as np
import os
import Raster
from multiprocessing import Pool
import util_ZB
import warnings



"""
1、用每个子流域裁剪dir、stremlink并存放在单独的文件夹中，以子流域命名
2、ArcgisD8->TauD8
3、读取这些路径并存放在（），统一放在[]
4、利用pool去并行划分边坡
"""
def Clip(Basin_path,dir_file,stream_file,DEM_file,LU_file,Slope_file,Out_path):
    """
    裁剪流向、河道，并存储在Out_path下的Dir、Stream，返回下一步的数据路径
    :param Basin_path:
    :param dir_file:
    :param stream_file:
    :param Out_path:
    :return:
    """
    # 构建文件树
    warnings.filterwarnings("ignore")
    if not os.path.exists(Out_path):
        os.mkdir(Out_path)
    Dir_out_path=os.path.join(Out_path,"Dir")
    stream_out_path=os.path.join(Out_path,"Stream")
    DEM_out_path=os.path.join(Out_path,"DEM")
    LU_out_path = os.path.join(Out_path, "LU")
    Slope_out_path = os.path.join(Out_path, "SLope")
    if not os.path.exists(Dir_out_path):
        os.mkdir(Dir_out_path)
    if not os.path.exists(stream_out_path):
        os.mkdir(stream_out_path)
    if not os.path.exists(DEM_out_path):
        os.mkdir(DEM_out_path)
    if not os.path.exists(LU_out_path):
        os.mkdir(LU_out_path)
    if not os.path.exists(Slope_out_path):
        os.mkdir(Slope_out_path)
    # 批量裁剪
    shp_list=os.listdir(Basin_path)
    # print(shp_list)
    n=0
    num=len(shp_list)
    para_list=[]
    for clip in shp_list:
        # print("{:.2f}%".format(n/num*100))
        n+=1
        # print(clip)
        if clip[-3:]=='shp':
            print(clip)
            Dir_outname=os.path.join(Out_path,"Dir","Dir_"+clip[:-4]+".tif")
            Stream_outname = os.path.join(Out_path, "Stream", "Stream" + clip[:-4] + ".tif")
            DEM_outname = os.path.join(Out_path, "DEM", "DEM" + clip[:-4] + ".tif")
            LU_outname = os.path.join(Out_path, "LU", "LU" + clip[:-4] + ".tif")
            Slope_outname = os.path.join(Out_path, "Slope", "Slope" + clip[:-4] + ".tif")
            # print(Dir_outname,Stream_outname)
            # os.path.join(Basin_path, clip)

            # cutlineDSName = os.path.join(Basin_path, clip),
            # cropToCutline = False,
            ds = gdal.Warp(DEM_outname, DEM_file, format='GTiff',
                           cutlineDSName=os.path.join(Basin_path, clip),
                           cropToCutline=False,
                           copyMetadata=True,
                           creationOptions=['COMPRESS=LZW', "TILED=True"]
                           )
            ds = gdal.Warp(Dir_outname, dir_file, format='GTiff',
                           cutlineDSName=os.path.join(Basin_path, clip),
                           cropToCutline=False,
                           copyMetadata=True,
                           creationOptions=['COMPRESS=LZW', "TILED=True"]
                           )
            ds = gdal.Warp(Stream_outname, stream_file, format='GTiff',
                           cutlineDSName=os.path.join(Basin_path, clip),
                           cropToCutline=False,
                           copyMetadata=True,
                           creationOptions=['COMPRESS=LZW', "TILED=True"]
                           )
            # LU
            if os.path.exists(LU_file):
                ds = gdal.Warp(LU_outname, LU_file, format='GTiff',
                               cutlineDSName=os.path.join(Basin_path, clip),
                               cropToCutline=False,
                               copyMetadata=True,
                               creationOptions=['COMPRESS=LZW', "TILED=True"]
                               )
            # Slope
            if Slope_file!=None and os.path.exists(Slope_file):
                ds = gdal.Warp(Slope_outname, Slope_file, format='GTiff',
                               cutlineDSName=os.path.join(Basin_path, clip),
                               cropToCutline=False,
                               copyMetadata=True,
                               creationOptions=['COMPRESS=LZW', "TILED=True"]
                               )
    # 将Arcgis_D8 -> TauDEM_D8
    # D8_Convert(Dir_out_path,Out_path)
    # out_TauD8_path = os.path.join(Out_path, "TauD8")
    out_TauD8_path = os.path.join(Out_path, "Dir")
    hillslope_out_path=os.path.join(Out_path,"HillSlope")


    return stream_out_path,out_TauD8_path,hillslope_out_path
def Clip_DEM_Dir_Stream_sd_hillslope(Basin_path, dir_file, stream_file,DEM_file ,LU_file,venu,Soil_file=None,process=3):
    Out_path=os.path.join(venu,"HillSlope")
    # Slope_file=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Test_Basin2\slope.tif'
    # 进行流向、河道的裁剪
    # LU_file = r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\HRU划分数据_0227\landuse.tif'
    stream_path, dir_path, out_path=Clip(Basin_path, dir_file, stream_file, DEM_file,LU_file,Soil_file,Out_path)   # out_path是r'....\HillSlope\'
    print('\n***************************************************************')
    print('|                                                              |')
    print('|             完成流向数据,河道数据的裁剪。                          |')
    print('|                                                              |')
    print('***************************************************************')
    if not os.path.join(Out_path):
        os.mkdir(Out_path)
    # 读取(stream,dir)并存放到[]
    parse=[]
    stream_list=os.listdir(stream_path)
    dir_list=os.listdir(dir_path)
    stream_num=len(stream_list)

    # 定义进程池
    po = Pool(process)

    for i in range(stream_num):
        # print(dir_list[i].split('_')[1][:-4])
        # parse.append((os.path.join(stream_path,stream_list[i]),os.path.join(dir_path,dir_list[i]),os.path.join(out_path,"hillslope"),dir_list[i][9:-4]))
        parse.append((os.path.join(stream_path, stream_list[i]), os.path.join(dir_path, dir_list[i]),
                      os.path.join(out_path), dir_list[i].split('_')[1][:-4]))
        # print((os.path.join(stream_path,stream_list[i]),os.path.join(dir_path,dir_list[i]),os.path.join(out_path),dir_list[i][9:-4]))
    # print(parse)
    num=len(parse)
    for j in parse:
        # print(j)
        # Divide_hillslope(j[0], j[1], j[2], j[3])
        # po.apply_async(Divide_hillslope, (j[0],j[1],j[2],j[3],))
        # print(j)
        po.apply_async(util_ZB.Hillslope_ZB, (j[0], j[1], j[2], j[3],))
    po.close()
    po.join()

if __name__=='__main__':
    # Basin_file = r'E:\青藏高原东部河流输出碳\DATA\LongRiver_simulation\LakeBasins_LongRiver\Level12.shp'
    # venu = r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Level12'
    # # Extract_Basin_by_Type.Extract_Basin_by_Type(Basin_file, venu)
    #
    # Basin_path=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Level12\1'
    # # out_path=os.path.join(venu,"HillSlope")
    # dir_file=r'E:\青藏高原东部河流输出碳\DATA\dir.tif'
    # DEM_file=r'E:\青藏高原东部河流输出碳\DATA\LongRiver_simulation\Merit_DEM.tif'
    # stream_file=r'E:\青藏高原东部河流输出碳\DATA\LongRiver_simulation\stream_link1.tif'
    #
    # Clip_DEM_Dir_Stream_sd_hillslope(Basin_path,dir_file,stream_file,DEM_file,venu)

    pass