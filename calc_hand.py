import multiprocessing
import os
import Raster
from osgeo import gdal
from numba import jit
import numpy as np
import jenkspy
from multiprocessing import Pool,Process
import math
import util_ZB
import new_discretize
import threading

dmove=[(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]
dmove_dic = {1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)}



def int322unint8(raster,int8_Stream_file):
    """
    把河网数据类型转成uint8，不然后面计算hand会出错
    :param raster:
    :return:
    """
    A=gdal.Open(raster)
    proj=A.GetProjection()
    geo_trans=A.GetGeoTransform()
    Raster=A.GetRasterBand(1).ReadAsArray()
    nodata1=A.GetRasterBand(1)
    nodata=nodata1.GetNoDataValue()
    # print(nodata)
    row,col=np.shape(Raster)
    res=np.zeros((row,col),dtype=np.int8)
    for i in range(row):
        for j in range(col):
            if Raster[i][j]!=nodata:
                res[i][j]=1
    # res[res!=1]=-1
    outband=gdal.GetDriverByName('GTIFF').Create(int8_Stream_file,col,row,1,gdal.GDT_Byte)
    outband.SetProjection(proj)
    outband.SetGeoTransform(geo_trans)
    B=outband.GetRasterBand(1)
    B.WriteArray(res)
    # B.SetNoDataValue(-9999)
    return int8_Stream_file
@jit(nopython=True)
def get_downstream_index(i, j, direction):
    if direction == 1:
        return i, j + 1
    if direction == 2:
        return i + 1, j + 1
    if direction == 4:
        return i + 1, j
    if direction == 8:
        return i + 1, j - 1
    if direction == 16:
        return i, j - 1
    if direction == 32:
        return i - 1, j - 1
    if direction == 64:
        return i - 1, j
    if direction == 128:
        return i - 1, j + 1

    return -1, -1
@jit(nopython=True)
def calc_hand(dir_arr, water_arr, elv_arr, mask_arr, result_arr, stack_arr):
    # calc_hand(流向，河流，高程，掩膜，结果，栈)

    rows, cols = dir_arr.shape
    length = 0

    for i in range(rows):
        for j in range(cols):
            # print(i,j,result_arr[i,j])
            #print(mask_arr[i][j])
            # 如果当前像元已经计算过HAND，则跳过
            if mask_arr[i, j] == 1:
                continue
            # 如果当前像元是水体，则 HAND = 0
            if water_arr[i, j] == 1:
                result_arr[i, j] = 0  # hand
                # print("Water",i,j)
                mask_arr[i, j] = 1
                continue

            next_i = i
            next_j = j
            flag = True
            stack_arr[length, 0] = next_i
            stack_arr[length, 1] = next_j
            length += 1
            # print(i,j,length)
            while flag is True:
                # 下游像元
                next_i, next_j = get_downstream_index(next_i, next_j, dir_arr[next_i, next_j])
                if 0 <= next_i < rows and 0 <= next_j < cols:  # 是否在范围内
                    # 如果汇入已知HAND的像元
                    if mask_arr[next_i, next_j] == 1 and result_arr[next_i, next_j] >= 0:

                        break
                    # 汇入边界外
                    elif mask_arr[next_i, next_j] == 1 and result_arr[next_i, next_j] < 0:
                        flag = False
                        # print("Out")
                        break
                    # 如果当前像元没有计算HAND并且是水体
                    elif water_arr[next_i, next_j] == 1:
                        mask_arr[next_i, next_j] = 1
                        result_arr[next_i, next_j] = 0

                        break
                    else:

                        stack_arr[length, 0] = next_i
                        stack_arr[length, 1] = next_j
                        length += 1

                # 如果下游像元超出范围
                else:

                    flag = False

            if flag is False:

                # 标记之前走过的像元
                while length > 0:
                    length -= 1
                    temp_i, temp_j = stack_arr[length, :]
                    mask_arr[temp_i, temp_j] = 1
            else:
                water_elv = elv_arr[next_i, next_j] - result_arr[next_i, next_j]
                while length > 0:

                    # 回溯，计算hand，标记之前走过的像元
                    length -= 1
                    temp_i, temp_j = stack_arr[length, :]
                    result_arr[temp_i, temp_j] = elv_arr[temp_i, temp_j] - water_elv

                    mask_arr[temp_i, temp_j] = 1
        # print(i,j,result_arr[i][j])
def cal_HAND(dir_tif, water_tif, elv_tif, out_tif):
    """
    计算hand
    :param dir_tif: 流向
    :param water_tif: 河流
    :param elv_tif: 高程
    :param out_tif: 输出HAND
    :return:
    """
    # main(流向，河流，高程，输出HAND)
    dirDs = gdal.Open(dir_tif)
    dir_arr = dirDs.ReadAsArray()

    elvDs = gdal.Open(elv_tif)
    elv_arr = elvDs.ReadAsArray()

    waterDs = gdal.Open(water_tif)
    waterBand = waterDs.GetRasterBand(1)
    water_nodata = waterBand.GetNoDataValue()  # 获取无意义值


    water_arr = waterDs.ReadAsArray()

    geo_trans = waterDs.GetGeoTransform()
    proj = waterDs.GetProjection()

    HAND_arr = np.full_like(elv_arr, fill_value=-9999.0)  # 创建相同大小矩阵并填充fill_value
    mask_arr = np.zeros(water_arr.shape, dtype=np.uint8)  # flag arr，判断该像元是否计算过
    mask_arr[water_arr == water_nodata] = 1  # 筛选无意义值并赋值为1

    total_size = water_arr.shape[0] * water_arr.shape[1]
    # stack_size = int(total_size / 100)  # 栈的大小
    stack_size = int(total_size)
    stack_arr = np.zeros((stack_size, 2), dtype=np.int32)
    dir_row,dir_col=dir_arr.shape
    dem_row,dem_col=elv_arr.shape
    if dir_row!=dem_row or dir_col!=dem_col:
        raise("Size is different")

    calc_hand(dir_arr, water_arr, elv_arr, mask_arr, HAND_arr, stack_arr)

    # outfile
    driver = gdal.GetDriverByName("GTiff")

    outDs = driver.Create(out_tif, HAND_arr.shape[1], HAND_arr.shape[0], 1, gdal.GDT_Float32,
                          ["COMPRESS=DEFLATE", "NUM_THREADS=8", "BIGTIFF=IF_SAFER"])
    outDs.SetGeoTransform(geo_trans)
    outDs.SetProjection(proj)
    outBand = outDs.GetRasterBand(1)

    outBand.SetNoDataValue(-9999.0)
    outBand.WriteArray(HAND_arr)

def main(venu,HAND_num=3,process=3):
    # '''
    Basin_path=os.path.join(venu,"HillSlope","HillSlope")
    Dir_path=os.path.join(venu,"HillSlope",'Dir')
    DEM_path=os.path.join(venu,"HillSlope",'DEM')
    Stream_path=os.path.join(venu,"HillSlope",'Stream')
    LU_path = os.path.join(venu, "HillSlope", 'LU')
    Slope_path=os.path.join(venu, "HillSlope", 'Slope')
    Basin_ID_list=os.listdir(Basin_path)
    print("开始拆分坡面...")
    para_list=[]
    for Basin_ID in Basin_ID_list:
        # print(Basin_ID)
        dir_file=os.path.join(Dir_path,"Dir_"+Basin_ID+'.tif')
        TauD8_dir_file=os.path.join(venu,"HillSlope",'TauD8',"TauD8_Dir"+Basin_ID+'.tif')
        DEM_file = os.path.join(DEM_path, "DEM" + Basin_ID + '.tif')
        # stream32=os.path.join(Basin_path,Basin_ID, "Stream" + Basin_ID + '_seq_'+Basin_ID+'.tif')
        stream32 = os.path.join(Stream_path, "Stream" + Basin_ID + '.tif')
        if os.path.exists(stream32):
            Stream_file=int322unint8(stream32,os.path.join(Basin_path,Basin_ID, "Stream" + Basin_ID + '.tif'))
        else:
            Stream_file=''
            # stream32=''

        HAND_file =os.path.join(Basin_path,Basin_ID,"HAND"+Basin_ID+".tif")
        hillslope_file=os.path.join(Basin_path,Basin_ID, "hillslope_" + Basin_ID + '.tif')

        # Stream_file_int32=os.path.join(Basin_path,Basin_ID, "Stream" + Basin_ID + '_seq_'+Basin_ID+'.tif')
        Basin_dir=os.path.join(Basin_path,Basin_ID)
        if os.path.exists(stream32):
            Merge_HAND_file=os.path.join(Basin_dir,"Merge_increase_HAND_" + str(Basin_ID) + '.tif')   # HAND分带后的合并体
        else:
            Merge_HAND_file=''
        Merge_HLU=os.path.join(Basin_dir,'HLU_Merge.tif')

        # LU
        LU_file=os.path.join(LU_path,"LU" + str(Basin_ID) + '.tif')
        if not os.path.exists(LU_file):
            LU_file=None
        # SLope
        Slope_file = os.path.join(Slope_path, "Slope" + str(Basin_ID) + '.tif')
        if os.path.exists(Slope_path):
            Slope_file=None

        # print([dir_file, Stream_file, DEM_file, HAND_file, hillslope_file, Stream_file_int32, Basin_dir, Merge_HAND_file])
        para_list.append([dir_file,Stream_file,DEM_file,HAND_file,hillslope_file,stream32,Basin_dir,Merge_HAND_file,TauD8_dir_file,Merge_HLU,LU_file,Slope_file,venu,Basin_ID])
        #                   0           1         2         3         4              5          6       7                8              9       10        11     12    13

    # ****************************** F1、只叠加土地利用、土壤、高程、子流域 ************************************
    # for para in para_list:
    #     new_discretize.Divide_By_HRU(venu,para[10],para[2],para[13],para[11])


    # ****************************** F2、张斌的新方法 ************************************
    # po = Pool(process)  # 定义一个进程池，最大进程数3
    for para in para_list:
        if para[1]!='':
            # po.apply_async(cal_HAND,(para[0],para[1],para[2],para[3],))
            cal_HAND(para[0],para[1],para[2],para[3])
    # po.close()
    # po.join()
    print('\n***************************************************************')
    print('|                                                              |')
    print('|             完成子流域HAND的计算。                               |')
    print('|                                                              |')
    print('***************************************************************')
    # 开始拆分坡面
    # po = Pool(process)  # 定义一个进程池，最大进程数3
    for para in para_list:
        if para[1] != '':
            # po.apply_async(func=new_discretize.Divde_Lake_HillSlope, args=(venu,para[0], para[1], para[10], para[11],para[3],))
            # a=po.apply_async(Divde_HillSlope, (venu,para[0], para[1], para[10], para[11],para[3],))
            # Divde_HillSlope(venu, para[0], para[1], para[10], para[11], para[3])
            new_discretize.Divde_Lake_HillSlope(venu, para[0], para[5], para[10], para[11],para[3],thresold1=123,thresold2=123)

    # ****************************** F3、土地利用和高程叠加 ************************************
    # for para in para_list:
    #     # print(para)
    #     # if flag>1:
    #     #     break
    #     if para[1] != '':
    #         # po.apply_async(func=new_discretize.Divde_Lake_HillSlope, args=(venu,para[0], para[1], para[10], para[11],para[3],))
    #     # flag+=1
    #         # a=po.apply_async(Divde_HillSlope, (venu,para[0], para[1], para[10], para[11],para[3],))
    #         # Divde_HillSlope(venu, para[0], para[1], para[10], para[11], para[3])
    #         new_discretize.Divide_By_HRU(venu,para[10],para[2],para[13],para[11])



if __name__ == "__main__":

    pass