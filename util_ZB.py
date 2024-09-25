import numpy as np
from osgeo import gdal,ogr,osr
import Raster
import os
import shutil
import math
import ZB_hillslope_workflow

dmove=[(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]
dmove_dic = {1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)}


gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
gdal.SetConfigOption("SHAPE_ENCODING", "GBK")

def Check_extent(row,col,x,y):
    if 0<=x<row and 0<=y<col:
        return True
    return False

def Check_self_intersect(Basin_shp_venu):
    """
    检查矢量文件是否存在空间自相交的问题，并解决
    :param Basin_shp_venu:
    :return:
    """

    Basin_list=os.listdir(Basin_shp_venu)
    shp_list=[file for file in Basin_list if file.endswith(".shp")]
    del Basin_list

    temp=os.path.join(os.path.dirname(Basin_shp_venu),"temp_1")
    if not os.path.exists(temp):
        os.mkdir(temp)
    for file in shp_list:
        save_path=os.path.join(temp,file)
        s_shp_si(os.path.join(Basin_shp_venu,file),save_path)

    shutil.rmtree(Basin_shp_venu)
    os.rename(temp,Basin_shp_venu)

def s_shp_si(shpFile,out_shp):
    # out_shp = shpFile[:-4] + '_ssi' + '.shp'
    # out_shp =shpFile
    # print(out_shp)
    # 打开数据
    ds = ogr.Open(shpFile, 0)
    if ds is None:
        print("打开文件 %s 失败！" % shpFile)
        return
    print("打开文件%s成功！" % shpFile)
    # 获取该数据源中的图层个数，一般shp数据图层只有一个，如果是mdb、dxf等图层就会有多个
    m_layer_count = ds.GetLayerCount()
    m_layer = ds.GetLayerByIndex(0)
    if m_layer is None:
        print("获取第%d个图层失败！\n", 0)
        return

    # 创建输出文件
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(out_shp):
        driver.DeleteDataSource(out_shp)
    outds = driver.CreateDataSource(out_shp)
    outlayer = outds.CreateLayer(out_shp[:-4], m_layer.GetSpatialRef(),geom_type=ogr.wkbPolygon)
    # 获取输出层的要素定义
    outLayerDefn = outlayer.GetLayerDefn()
    # 对图层进行初始化，如果对图层进行了过滤操作，执行这句后，之前的过滤全部清空
    m_layer.ResetReading()
    # 获取投影
    prosrs = m_layer.GetSpatialRef()
    # 添加字段
    inLayerDefn = m_layer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outlayer.CreateField(fieldDefn)

    # loop through the input features
    m_feature = m_layer.GetNextFeature()
    while m_feature:
        # print(m_feature)
        o_geometry = m_feature.GetGeometryRef()
        # 关键，合并几何
        o_geometry = o_geometry.Union(o_geometry)
        outfeature = ogr.Feature(outLayerDefn)
        outfeature.SetGeometry(o_geometry)
        # 遍历每个要素的字段，并设置字段属性
        for i in range(0, outLayerDefn.GetFieldCount()):
            # print(outLayerDefn.GetFieldDefn(i).GetNameRef())
            outfeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), m_feature.GetField(i))
        outlayer.CreateFeature(outfeature)
        # dereference the features and get the next input feature
        outfeature = None
        m_feature = m_layer.GetNextFeature()


    outds.Destroy()

def get_rever_D8(dir, row, col):
    """
    查询输入栅格的上游栅格
    :param dir: array of dir
    :param row: row of the cell
    :param col:
    :return: [(i,j),(),]
    """
    up_cell = []
    row_num, col_num = dir.shape

    for i in range(8):
        now_loc = (row + dmove[i][0], col + dmove[i][1])
        # print(now_loc)
        if 0<=now_loc[0]<row_num and 0<=now_loc[1]<col_num:
            if dir[now_loc[0], now_loc[1]] == 2 ** ((i + 4) % 8):
                up_cell.append(now_loc)
                # print(dir[now_loc[0], now_loc[1]] , 2 ** ((i + 4) % 7))
                # if HAND[now_loc[0],now_loc[1]]==now_HAND:
                #     # 如果属于相同的HAND带，则为上游
                #     up_cell.append(now_loc)
    return up_cell

def bfs_all(id,arr):
    """
        搜索所有id的块集合
        :param id: 当前搜索集合的id
        :param i:
        :param j:
        :param arr:
        :param vis:
        :return:
        """

    row, col = arr.shape
    vis=np.zeros((row,col))
    flag=False
    res={id:[]}
    for i in range(row):
        for j in range(col):
            if arr[i,j]==id and vis[i,j]==0:

                pop_list = [(i, j)]
                collection_list = [(i, j)]
                vis[i, j] = 1
                while pop_list:
                    pop_cell = pop_list.pop()
                    for k in range(8):
                        now_cell_x = pop_cell[0] + dmove[k][0]
                        now_cell_y = pop_cell[1] + dmove[k][1]
                        if Check_extent(row, col, now_cell_x, now_cell_y):
                            if arr[now_cell_x, now_cell_y] == id:
                                if vis[now_cell_x, now_cell_y] == 0:
                                    pop_list.insert(0, (now_cell_x, now_cell_y))
                                    collection_list.insert(0, (now_cell_x, now_cell_y))
                                    vis[now_cell_x, now_cell_y] = 1
                res[id].append(collection_list)
    return res

def bfs(id,i,j,arr,vis):
    """
    搜索块集合，并标记vis=1
    :param id: 当前搜索集合的id
    :param i:
    :param j:
    :param arr:
    :param vis:
    :return:
    """

    row,col=arr.shape
    pop_list=[(i,j)]
    collection_list=[(i,j)]
    vis[i,j]=1
    while pop_list:
        pop_cell=pop_list.pop()
        for k in range(8):
            now_cell_x=pop_cell[0]+dmove[k][0]
            now_cell_y=pop_cell[1]+dmove[k][1]
            if Check_extent(row,col,now_cell_x,now_cell_y):
                if arr[now_cell_x,now_cell_y]==id:
                    if vis[now_cell_x,now_cell_y]==0:
                        pop_list.insert(0,(now_cell_x,now_cell_y))
                        collection_list.insert(0,(now_cell_x,now_cell_y))
                        vis[now_cell_x,now_cell_y]=1

    return vis,collection_list

def Hillslope_ZB(Stream_file,Dir_file,hillslope_dir,BasinID):
    if not os.path.exists(hillslope_dir):
        os.mkdir(hillslope_dir)
    Basin_dir=os.path.join(hillslope_dir,BasinID)
    if not os.path.exists(Basin_dir):
        os.mkdir(Basin_dir)
    #os.path.join(out_path,"hillslope")
    #(streamf, flowdirf, hillslpf,BasinID_path)
    Stream = Raster.get_raster(Stream_file)
    # DEM = Raster.get_raster(DEM_file)
    Dir = Raster.get_raster(Dir_file)
    proj, geo, nodata = Raster.get_proj_geo_nodata(Stream_file)
    _, _1, dir_nodata = Raster.get_proj_geo_nodata(Dir_file)
    # _,_1,DEM_nodata=Raster.get_proj_geo_nodata(DEM_file)
    # max_Stream_id=Stream.max()  # 用来给新生成的河段编码
    # print(max_Stream_id)
    HillSlope=np.zeros_like(Stream)     # np.zeros_like是复制相同的属性数组，包括数据类型！

    HillSlope[:,:]=-9999
    # print(HillSlope)
    # 1、找到源头
    print('*********************************************************************************')
    print('*                                                                                *')
    print('*                                 Start Preprocessing!                           *')
    print('*                                                                                *')
    print('*********************************************************************************')
    row, col = Stream.shape
    Stream_dic = {}  # id:[(X,Y),...]
    for i in range(row):
        for j in range(col):
            if Stream[i, j] != nodata:
                Stream_dic.setdefault(Stream[i, j], []).append((i, j))
    # print(len(Stream_dic))

    for stream_id in Stream_dic:
        stream_cell_list = Stream_dic[stream_id]
        new_stream_list = []
        for cell in stream_cell_list:
            now_stream_id = Stream[cell[0], cell[1]]
            upstream_list = get_rever_D8(Dir, cell[0], cell[1])
            flag = True

            for up_cell in upstream_list:  # 判断是否为源头
                if up_cell in stream_cell_list:
                    flag = False
                    break

            if flag:
                # print(cell)
                new_stream_list.append(cell)
                # 开始寻找下游
                pop_list = [cell]
                while pop_list:
                    pop_cell = pop_list.pop()

                    pop_dir = Dir[pop_cell[0], pop_cell[1]]
                    # if pop_dir != dir_nodata and pop_dir != 255:
                    if pop_dir in dmove_dic:
                        # print(pop_cell,pop_dir)
                        next_x = pop_cell[0] + dmove_dic[pop_dir][0]
                        next_y = pop_cell[1] + dmove_dic[pop_dir][1]
                        # 确保河流流向合法区域
                        if (next_x, next_y) in stream_cell_list:
                            new_stream_list.append((next_x, next_y))
                            pop_list.append((next_x, next_y))
                    else:
                        if pop_dir != dir_nodata and pop_dir != 255:
                            # print(pop_dir)
                            pass

                break
        Stream_dic[stream_id] = new_stream_list.copy()

    # print(Stream_dic)
    # print(len(Stream_dic))
    ids=list(Stream_dic.keys())
    min_stream=min(ids)
    max_stream=max(ids)

    print('*********************************************************************************')
    print('*                                                                                *')
    print('*                                 find all Stream!                               *')
    print('*                                                                                *')
    print('*********************************************************************************')

    # 寻找划源头坡的河网，源头为河源上游河流栅格的stream_id不等于当前id，并且都不为nodata
    for stream_id in Stream_dic:
        Stream_Head=Stream_dic[stream_id][0]
        # 判断源头
        upcell_list=get_rever_D8(Dir,Stream_Head[0],Stream_Head[1])
        # print(upcell_list)
        flag=True

        # 判断是否源头在边缘，这种就说明上游河流是上个子流域的
        for i in range(8):
            next_X = Stream_Head[0] + dmove[i][0]
            next_Y = Stream_Head[1] + dmove[i][1]
            if Check_extent(row, col, next_X, next_Y):
                if Dir[next_X, next_Y] == dir_nodata:
                    flag = False
            else:
                flag = False

        for cell in upcell_list:
            if Dir[cell[0],cell[1]]==dir_nodata:
                flag=False
                break
        # 不是边缘源头,再进一步判断是否划分源头坡(通过判断上游栅格是否存在河流栅格：YES，不划HEAD；NO，划HEAD)
        if flag:
            # print(Stream_Head)
            for cell in upcell_list:
                if Stream[cell[0],cell[1]]!=nodata:
                    flag=False
                    break
        if flag:
            # 此时可划源头坡
            # print(Stream_Head)
            HillSlope=HEAD_HillSlope(Stream_Head,HillSlope,Dir,stream_id*3+max_stream)

            Stream_dic[stream_id].remove(Stream_Head)
    # print(Stream_dic)

    # 划分左右边坡
    for stream_id in Stream_dic:
        # print("Stream_id",stream_id)
        Stream_cell=Stream_dic[stream_id]
        Left=[]
        Right=[]
        for cell in Stream_cell:
            up=-1
            down=-1
            up_stream_cell=get_rever_D8(Dir,cell[0],cell[1])

            for i in range(8):
                next_X=cell[0]+dmove[i][0]
                next_Y=cell[1]+dmove[i][1]
                if Check_extent(row,col,next_X,next_Y):
                    if (next_X,next_Y) in up_stream_cell:
                        # print(next_Y)
                        if Stream[next_X, next_Y] != nodata:
                            up=i
                            up_stream_cell.remove((next_X,next_Y))
                    else:
                        if Stream[next_X,next_Y]!=nodata:
                            down=i
            # print(up_stream_cell)
            # print(up,down)
            # 开始划分左右边坡，规则如下
            # 如果up=0,更新up=6，
            # 如果down=0，更新down=2
            # if up>down:划右坡为[down,up]，补左坡
            # if up<down:划左坡为[up,down]，补右坡
            if up==-1:
                up=(down+4)%8
            if down==-1:
                down=(up+4)%8
            if up>down:
                down += 1
                up += 1
                for i in range(8):
                    next_X = cell[0] + dmove[i][0]
                    next_Y = cell[1] + dmove[i][1]
                    # print(up,down,i)
                    if down<=i<up:
                        if (next_X,next_Y) in up_stream_cell:
                            Right.append((next_X,next_Y))
                    else:
                        if (next_X,next_Y) in up_stream_cell:
                            Left.append((next_X,next_Y))
            else:
                if up<down:
                    down += 1
                    up += 1
                    for i in range(8):
                        next_X = cell[0] + dmove[i][0]
                        next_Y = cell[1] + dmove[i][1]
                        if up <= i < down:
                            if (next_X, next_Y) in up_stream_cell:
                                Left.append((next_X, next_Y))
                        else:
                            if (next_X, next_Y) in up_stream_cell:
                                Right.append((next_X, next_Y))

        # 开始追溯左右坡上游
        # print(Left)
        # print(stream_id)
        HillSlope = Up_HillSlope(Left, HillSlope, Dir, stream_id * 3 + max_stream + 1)
        HillSlope = Up_HillSlope(Right, HillSlope, Dir, stream_id * 3 + max_stream + 2)
    hillslope_file=os.path.join(Basin_dir,"hillslope_"+str(BasinID)+'.tif')
    # Raster.save_raster(hillslope_file, HillSlope, proj, geo, gdal.GDT_Float64, -9999)
    # print(HillSlope)
    Raster.save_raster(hillslope_file,HillSlope,proj,geo,gdal.GDT_Float32,-9999)

    pass

def Up_HillSlope(up_cell_list,HillSlope,Dir,Head_id):
    """
    划分cell列表，往上游追溯，
    :param HEAD:
    :param HillSlope:
    :return:
    """
    # up_cell_list=[HEAD]
    # print(Head_id)
    while up_cell_list:
        pop_cell=up_cell_list.pop()
        up_cell=get_rever_D8(Dir,pop_cell[0],pop_cell[1])
        HillSlope[pop_cell[0],pop_cell[1]]=Head_id

        up_cell_list+=up_cell
    return HillSlope

def HEAD_HillSlope(HEAD,HillSlope,Dir,Head_id):
    """
    划分源头坡，输入源头X,Y，往上游追溯，
    :param HEAD:
    :param HillSlope:
    :return:
    """
    up_cell_list=[HEAD]
    while up_cell_list:
        pop_cell=up_cell_list.pop()
        up_cell=get_rever_D8(Dir,pop_cell[0],pop_cell[1])
        HillSlope[pop_cell[0],pop_cell[1]]=Head_id

        up_cell_list+=up_cell
    return HillSlope

if __name__=='__main__':

    pass
