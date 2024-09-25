import math
import time
import os
import numpy as np
from osgeo import gdal,ogr
import Raster
import util_ZB
import jenkspy
dmove=[(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]
dmove_dic = {1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)}

def Divde_Lake_HillSlope(venu,Dir_file,Stream_file,LU_file,Slope_file,HAND_file,thresold1=123,thresold2=123):

    # 输出到
    # venu=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Test_Basin2'
    out_path=os.path.join(venu,'HRU')
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    dir_name,file_name=os.path.split(Stream_file)
    Basin_id=file_name[6:-4]
    # print(Basin_id)
    Basin_dir=os.path.join(out_path,Basin_id)
    if not os.path.exists(Basin_dir):
        os.mkdir(Basin_dir)
    # out_file
    Stream=Raster.get_raster(Stream_file)
    proj,geo,streamnodata=Raster.get_proj_geo_nodata(Stream_file)
    Dir=Raster.get_raster(Dir_file)
    _,_,dir_nodata=Raster.get_proj_geo_nodata(Dir_file)
    # row,col=Stream.shape
    # LU=Raster.get_raster(LU_file)
    # Slope=Raster.get_raster(Slope_file)
    HAND=Raster.get_raster(HAND_file)


# **************坡面、整理****************
    row, col = Stream.shape

    if row*col<thresold1:
        result_arr=np.zeros((row,col),float)
        result_arr[:,:]=-9999
        result_arr[Dir!=dir_nodata]=1
        Raster.save_raster(os.path.join(Basin_dir, 'HRU' + Basin_id + '.tif'), result_arr, proj,
                           geo, gdal.GDT_Float32, -9999)

        print('开始写入流向文件')
        # # 写入txt
        fields_file = os.path.join(venu, 'ALL_HRU_fields' + '.txt')
        Note = open(fields_file, mode='w')
        info = ['FID    downstreamFID    subbasin\n']
        # for HRU_id in downstream_dic:
        #     info.append(str(HRU_id)+'    '+str(downstream_dic[HRU_id][0])+'    '+str(Basin_id)+'\n')
        final_HRU_downstream = ['FID    downstreamFID    subbasin\n','1    -1    '+str(Basin_id)]
        Note.writelines(final_HRU_downstream)
        Note.close()
        print('成功写入流向文件')
        return
    # HillSlope = np.zeros_like(Stream)  # np.zeros_like是复制相同的属性数组，包括数据类型！
    HillSlope = np.zeros((row,col),float)
    HillSlope[:, :] = -9999
    # ************************************加入直接流入湖泊的坡面，编码为Basin_id+max_stream *******************************************
    HillSlope[Dir != dir_nodata] = -9999

    Stream_dic = {}  # id:[(X,Y),...]

    # 寻找所有的河网栅格，按照河流id进行存储（无序）
    for i in range(row):
        for j in range(col):
            if Stream[i, j] != streamnodata:
                Stream_dic.setdefault(Stream[i, j], []).append((i, j))
    # print(Stream_dic)

    # 对每条河流进行排序，“源头-中间栅格-汇”
    for stream_id in Stream_dic:
        stream_cell_list = Stream_dic[stream_id]
        new_stream_list = []

        # 寻找当前id的河流源头
        for cell in stream_cell_list:
            now_stream_id = Stream[cell[0], cell[1]]
            upstream_list = util_ZB.get_rever_D8(Dir, cell[0], cell[1])
            flag = True

            for up_cell in upstream_list:  # 判断是否为源头:上游都不是河流
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
                            print(pop_dir)

                break
        Stream_dic[stream_id] = new_stream_list.copy()

    # print(Stream_dic)
    # print(len(Stream_dic))
    id_s = list(Stream_dic.keys())
    # min_stream = min(id_s)
    if len(id_s)==0:
        return
    max_stream = max(id_s)
    # for i in Stream_dic:
    #     print(i,':',Stream_dic[i])
    print('*********************************************************************************')
    print('*                                                                                *')
    print('*                                 find all Stream!                               *')
    print('*                                                                                *')
    print('*********************************************************************************')

    # 寻找划源头坡的河网，源头为河源上游河流栅格的stream_id不等于当前id，并且都不为nodata
    All_Head = {}
    for stream_id in Stream_dic:
        Stream_Head = Stream_dic[stream_id][0]
        # 判断源头
        upcell_list = util_ZB.get_rever_D8(Dir, Stream_Head[0], Stream_Head[1])
        # print(upcell_list)
        flag = True

        # 判断是否源头在边缘，这种就说明上游河流是上个子流域的
        for i in range(8):
            next_X = Stream_Head[0] + dmove[i][0]
            next_Y = Stream_Head[1] + dmove[i][1]
            if util_ZB.Check_extent(row, col, next_X, next_Y):
                if Dir[next_X, next_Y] == dir_nodata:
                    flag = False
            else:
                flag = False

        for cell in upcell_list:
            if Dir[cell[0], cell[1]] == dir_nodata:
                flag = False
                break
        # 不是边缘源头,再进一步判断是否划分源头坡(通过判断上游栅格是否存在河流栅格：YES，不划HEAD；NO，划HEAD)
        if flag:
            # print(Stream_Head)
            for cell in upcell_list:
                if Stream[cell[0], cell[1]] != streamnodata:
                    flag = False
                    break
        if flag:
            All_Head.setdefault(stream_id, [Stream_Head])
            # 此时可划源头坡
            # print(Stream_Head)
            HillSlope = util_ZB.HEAD_HillSlope(Stream_Head, HillSlope, Dir, stream_id * 3 + max_stream)

            Stream_dic[stream_id].remove(Stream_Head)


    # 划分左右边坡
    # 根据流向向上追溯，得到划分的斑块河道
    All_Left={}
    All_Righ={}

    for stream_id in Stream_dic:
        # print("Stream_id", stream_id)
        Stream_cell = Stream_dic[stream_id]
        Left=[]
        Right = []
        for cell in Stream_cell:
            up = -1
            down = -1
            up_stream_cell = util_ZB.get_rever_D8(Dir, cell[0], cell[1])
            # Left.append(cell)
            for i in range(8):
                next_X = cell[0] + dmove[i][0]
                next_Y = cell[1] + dmove[i][1]
                if util_ZB.Check_extent(row, col, next_X, next_Y):
                    if (next_X, next_Y) in up_stream_cell:
                        # print(next_Y)
                        if Stream[next_X, next_Y] != streamnodata:
                            up = i
                            up_stream_cell.remove((next_X, next_Y))
                    else:
                        if Stream[next_X, next_Y] != streamnodata:
                            down = i
            # print(up_stream_cell)
            # print(up,down)
            # 开始划分左右边坡，规则如下
            # 如果up=0,更新up=6，
            # 如果down=0，更新down=2
            # if up>down:划右坡为[down,up]，补左坡
            # if up<down:划左坡为[up,down]，补右坡
            if up == -1:
                up = (down + 4) % 8
            if down == -1:
                down = (up + 4) % 8
            if up > down:
                down += 1
                up += 1
                for i in range(8):
                    next_X = cell[0] + dmove[i][0]
                    next_Y = cell[1] + dmove[i][1]
                    # print(up,down,i)
                    if down <= i < up:
                        if (next_X, next_Y) in up_stream_cell:
                            Right.append((next_X, next_Y))
                    else:
                        if (next_X, next_Y) in up_stream_cell:
                            Left.append((next_X, next_Y))
            else:
                if up < down:
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
        # print(Left, Right)
        All_Righ.setdefault(stream_id,Right.copy())
        All_Left.setdefault(stream_id,Left.copy())
        # 开始追溯左右坡上游
        # print(Left)
        # print(stream_id)
        HillSlope = util_ZB.Up_HillSlope(Left, HillSlope, Dir, stream_id * 3 + max_stream + 1)
        HillSlope = util_ZB.Up_HillSlope(Right, HillSlope, Dir, stream_id * 3 + max_stream + 2)


    # 存储边坡
    # Raster.save_raster(os.path.join(Basin_dir,'HillSlope'+Basin_id+'.tif'),HillSlope,proj,geo,gdal.GDT_Float32,-9999)
    # del HillSlope


    # 开始追溯上游
    id = 0
    ids = np.zeros((row, col), dtype=float)
    ids[:, :] = -9999
    sum_id = 0
    # id = 0
    id_len = {}

    stream_upstream={}
    start_id=[]
    end_id=[]
    for stream_id in Stream_dic:
        # print(stream_id)
        # 源头坡
        if stream_id in All_Head:
            # print(stream_id,All_Head)
            for head in All_Head[stream_id]:
                # print(head)
                len1 = 0
                # ids[head[0], head[1]] = id
                pop_cells = [head]
                # upstream=util_ZB.get_rever_D8(Dir,i,j)
                stream_upstream[id] = []
                while pop_cells:
                    pop_cell = pop_cells.pop()


                    stream_upstream[id].append(pop_cell)
                    len1 += 1
                    ids[pop_cell[0], pop_cell[1]] = id
                    upstream = util_ZB.get_rever_D8(Dir, pop_cell[0], pop_cell[1])
                    # print(upstream)
                    for cell in upstream:
                        if Stream[cell[0], cell[1]] == streamnodata:
                            pop_cells.append(cell)
                            # ids[cell[0],cell[1]]=ids[pop_cell[0],pop_cell[1]]+1

                    # print(len)
                id_len[id] = len1
                sum_id += len1
                id += 1
                ids[head[0],head[1]]=-9999
        start_id.append(id)
        # 左边坡
        for head in All_Left[stream_id]:
                # print(head)
            len1 = 0
            # ids[head[0], head[1]] = id
            pop_cells = [head]
                # upstream=util_ZB.get_rever_D8(Dir,i,j)
            stream_upstream[id]=[]
            while pop_cells:
                pop_cell = pop_cells.pop()
                stream_upstream[id].append(pop_cell)
                len1 += 1
                ids[pop_cell[0], pop_cell[1]] = id
                upstream = util_ZB.get_rever_D8(Dir, pop_cell[0], pop_cell[1])
                    # print(upstream)
                for cell in upstream:
                    if Stream[cell[0], cell[1]] == streamnodata:
                        pop_cells.append(cell)
                            # ids[cell[0],cell[1]]=ids[pop_cell[0],pop_cell[1]]+1

                # print(len)
            id_len[id] = len1
            sum_id += len1
            id += 1
        # 右边坡
        for head in All_Righ[stream_id]:
                # print(head)
            len1 = 0
            # ids[head[0], head[1]] = id
            pop_cells = [head]
                # upstream=util_ZB.get_rever_D8(Dir,i,j)
            stream_upstream[id]=[]
            while pop_cells:
                pop_cell = pop_cells.pop()
                stream_upstream[id].append(pop_cell)
                len1 += 1
                ids[pop_cell[0], pop_cell[1]] = id
                upstream = util_ZB.get_rever_D8(Dir, pop_cell[0], pop_cell[1])
                    # print(upstream)
                for cell in upstream:
                    if Stream[cell[0], cell[1]] == streamnodata:
                        pop_cells.append(cell)
                            # ids[cell[0],cell[1]]=ids[pop_cell[0],pop_cell[1]]+1

                # print(len)
            id_len[id] = len1
            sum_id += len1
            id += 1
        end_id.append(id)
    # print(stream_upstream)
    Raster.save_raster(os.path.join(Basin_dir,'patch'+Basin_id+'.tif'), ids, proj,
                           geo, gdal.GDT_Float32, -9999)



    num=id
    # 合并相邻河道的上游
    # avg = sum_id / num

    # 阈值可调
    avg= thresold2##123#30 #50 #123 # 10  #123


    # print(id_len)
    # print(avg)
    new_id = 2000
    # ids1 = np.zeros((row, col), dtype=float)
    # ids1[:, :] = -9999

    # 沿河道合并较小的上游
    noprocess_id = []



    # 统计各上游的面积
    new_id_len = {}
    sum_id = 0

    no_precess_ids=[]
    for id in id_len:
        # print(id)
        # print(id)
        if id_len[id] <= avg:
            # 合并
            ids[ids == id] = new_id
            # sum_id += sum(ids[ids == new_id]) / new_id
            new_id_len[new_id] = sum_id

        else:
            noprocess_id.append(id)
    Raster.save_raster(os.path.join(Basin_dir, 'trial_1' + Basin_id + '.tif'), ids, proj,
                       geo, gdal.GDT_Float32, -9999)

    # 四联通标记+bfs拆分小单元
    new_noprocess_ids=[]
    def bfs_4(ids):
        dmove_4=[(0,1),(1,0),(0,-1),(-1,0)]
        row,col=ids.shape
        vis=np.zeros((row,col))

        id=300
        for i in range(row):
            for j in range(col):
                flag=ids[i, j]
                if vis[i,j]==0 and flag!=-9999:
                    # 开始寻找
                    save_cells = []
                    # print(flag)
                    pop_cells=[(i,j)]
                    vis[i,j]=1
                    while pop_cells:
                        pop_cell=pop_cells.pop()
                        save_cells.append(pop_cell)
                        # ids[pop_cell[0],pop_cell[1]]=id
                        # 如果相邻的8个像元存在河流，那么只进行4连通；否则进行8连通
                        stream_flag=False
                        for k in range(8):
                            next_cell = (pop_cell[0] + dmove[k][0], pop_cell[1] + dmove[k][1])
                            if 0 <= next_cell[0] < row and 0 <= next_cell[1] < col:
                                if Stream[next_cell[0],next_cell[1]]!=streamnodata:
                                    # 4连通
                                    stream_flag=True
                        if stream_flag:
                            # 4连通
                            for k in range(4):
                                next_cell=(pop_cell[0]+dmove_4[k][0],pop_cell[1]+dmove_4[k][1])
                                if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                                    if vis[next_cell[0],next_cell[1]]==0 and ids[next_cell[0],next_cell[1]]==flag and Stream[next_cell[0],next_cell[1]]==streamnodata:
                                        pop_cells.append(next_cell)
                                        vis[next_cell[0],next_cell[1]]=1
                        else:
                            # 8连通
                            for k in range(8):
                                next_cell = (pop_cell[0] + dmove[k][0], pop_cell[1] + dmove[k][1])
                                if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                                    if vis[next_cell[0],next_cell[1]]==0 and ids[next_cell[0],next_cell[1]]==flag and Stream[next_cell[0],next_cell[1]]==streamnodata:
                                        pop_cells.append(next_cell)
                                        vis[next_cell[0],next_cell[1]]=1

                    # if ids[save_cells[0][0],save_cells[0][1]] in noprocess_id:
                    #     new_noprocess_ids.append(id)

                    new_noprocess_ids.append(id)
                    for cell in save_cells:

                        ids[cell[0],cell[1]]=id
                    id+=1
                    # print(id)
        return ids,id

    ids,max_id=bfs_4(ids.copy())

    Raster.save_raster(os.path.join(Basin_dir, 'trial' + Basin_id + '.tif'), ids, proj,
                       geo, gdal.GDT_Float32, -9999)

    # 追溯下游，构建汇流关系
    patch_ids=np.unique(ids)
    for id in patch_ids:
        num=sum(ids[ids==id])/id
        # if num==1:
        if num < 9:
            # 分3种情况，
            # （1）如果是河流像元，pass
            # （2）如果下游是河流，则追溯上游：A、上游不为空，合并；B、上游为空，合并到最近的同坡面相邻集合
            # （3）下游不是河流，则追溯下游，直到遇见和自己不同的集合，合并

            index=np.argwhere(ids==id)

            start_cell=index[0]
            # print(start_cell)
            x=start_cell[0]
            y=start_cell[1]
            if Stream[start_cell[0], start_cell[1]] != streamnodata:
                ids[start_cell[0], start_cell[1]] = Stream[start_cell[0], start_cell[1]]
                continue

            cell_dir = Dir[start_cell[0], start_cell[1]]
            if cell_dir not in dmove_dic:
                return
            next_cell = (start_cell[0] + dmove_dic[cell_dir][0], start_cell[1] + dmove_dic[cell_dir][1])
            if 0 <= next_cell[0] < row and 0 <= next_cell[1] < col:

                if Stream[next_cell[0], next_cell[1]] != streamnodata:
                    # 下游是河流，id赋值为上游id
                    upstreams = util_ZB.get_rever_D8(Dir, start_cell[0], start_cell[1])
                    if len(upstreams)!=0:
                        new_id = ids[upstreams[0][0], upstreams[0][1]]
                        ids[x,y] = new_id

                    else:
                        pop_cells=[(x,y)]
                        vis=np.zeros((row,col))
                        vis[x,y] = 1
                        while pop_cells:
                            pop_cell=pop_cells.pop()
                            vis[pop_cell[0], pop_cell[1]] = 1
                            for k in range(8):
                                next_cell=(pop_cell[0]+dmove[k][0],pop_cell[1]+dmove[k][1])
                                if 0 <= next_cell[0] < row and 0 <= next_cell[1] < col:
                                    if Stream[next_cell[0],next_cell[1]]==streamnodata and HillSlope[x,y]==HillSlope[next_cell[0],next_cell[1]]:

                                        if ids[next_cell[0],next_cell[1]]!=-9999 and len(ids[ids==ids[next_cell[0],next_cell[1]]])>9:
                                            # print(len(ids[ids==ids[next_cell[0],next_cell[1]]]))

                                            ids[x, y] = ids[next_cell[0],next_cell[1]]
                                            break
                                        else:
                                            if vis[next_cell[0],next_cell[1]]!=1:
                                                pop_cells.append(next_cell)


                    continue

            while True:
                # if id==
                # print(id,i,j,x,y,start_cell)
                cell_dir=Dir[start_cell[0],start_cell[1]]
                if cell_dir not in dmove_dic:
                    return
                next_cell=(start_cell[0]+dmove_dic[cell_dir][0],start_cell[1]+dmove_dic[cell_dir][1])
                if 0<=next_cell[0]<row and 0<=next_cell[1]<col:

                    cell_id = ids[next_cell[0], next_cell[1]]
                    if Stream[next_cell[0],next_cell[1]]!=streamnodata:
                        # 下游是河流，id赋值为上游id
                        # upstreams=util_ZB.get_rever_D8(Dir,start_cell[0],start_cell[1])
                        # new_id=ids[upstreams[0][0],upstreams[0][1]]
                        ids[x,y]=cell_id

                        break
                    else:
                        # print(i,j)
                        start_cell=next_cell

    # Raster.save_raster(os.path.join(Basin_dir,'process_patch'+Basin_id+'.tif'), ids, proj,
    # geo, gdal.GDT_Float32, -9999)

    # 对没有处理过的上游进行HAND带划分，其他的合并的因为上游面积过小，不再进行HAND带划分
    # import jenkspy
    # print(new_noprocess_ids)
    process_ids=[]
    for id in new_noprocess_ids:
        # print(id)
        HANDS=HAND[ids==id]
        HANDS_cell=np.argwhere(ids==id)
        # print(HANDS_cell)
        # print(HANDS)
        # print(id, len(HANDS))
        if len(HANDS)>6:
            try:
                breaks = jenkspy.jenks_breaks(HANDS,3)
                # print(breaks)
                di=3
                i=3
                while i>0:
                    for cell in HANDS_cell:
                        if HAND[cell[0],cell[1]]<=math.ceil(breaks[i]):
                            ids[cell[0],cell[1]]=max_id
                    process_ids.append(max_id)
                    max_id+=1
                    # i-=di
                    i-=1
            except:
                print(id)
    # print(process_ids)
    Raster.save_raster(os.path.join(Basin_dir, 'process_patch1' + Basin_id + '.tif'), ids, proj,
                       geo, gdal.GDT_Float32, -9999)
    # print(process_ids)
    for id in process_ids:
        # 用bfs寻找最大联通矩阵，把小于某一阈值的合并到下游
        res=util_ZB.bfs_all(id,ids)
        # print(res)
        # 使用平均值剔除
        areas=np.array([len(cells) for cells in res[id]])
        mean_data=areas.mean()
        flag=False
        for area in areas:
            if area<10:
                flag=True
        if flag:
            for collection in res[id]:
                if len(collection)<=mean_data:
                    # 寻找最近的面积大于平均值的下游，合并至此
                    pop_cells=[collection[0]]
                    # pop_cells=collection.copy()
                    while pop_cells:
                        pop_cell=pop_cells.pop()
                        cell_dir=Dir[pop_cell[0],pop_cell[1]]
                        if cell_dir not in dmove_dic:
                            return
                        next_cell=(pop_cell[0]+dmove_dic[cell_dir][0],pop_cell[1]+dmove_dic[cell_dir][1])
                        if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                            if ids[next_cell[0],next_cell[1]]!=id and ids[next_cell[0],next_cell[1]]!=-9999:
                                # 合并到这
                                new_id=ids[next_cell[0],next_cell[1]]
                                breaks
                    for cell in collection:
                        ids[cell[0],cell[1]]=new_id
                else:
                    for cell in collection:
                        ids[cell[0],cell[1]]=max_id
                    max_id+=1
    # Raster.save_raster(os.path.join(Basin_dir, 'HRU_2' + Basin_id + '.tif'), ids, proj,
    #                    geo, gdal.GDT_Float32, -9999)

    # 存在一些空白像元，不知道啥原因，直接合并到下游
    for i in range(row):
        for j in range(col):
            if HAND[i,j]!=-9999 and ids[i,j]==-9999:
                # 合并到最近的下游id不为-9999的带
                pop_cells=[(i,j)]
                while pop_cells:
                    pop_cell=pop_cells.pop()
                    cell_dir=Dir[pop_cell[0],pop_cell[1]]
                    if cell_dir not in dmove_dic:
                        # print(cell_dir,'***************************************')
                        continue
                    next_cell=(i+dmove_dic[cell_dir][0],j+dmove_dic[cell_dir][1])
                    if 0<=next_cell[0]<row and 0<=next_cell[1]<col :
                        if ids[next_cell[0],next_cell[1]]!=-9999:
                            ids[i,j]=ids[next_cell[0],next_cell[1]]
                            break

    # 拆分空间不连续集合
    result_arr=np.zeros_like(ids)
    result_arr[:,:]=-9999
    vis=np.zeros_like(result_arr)
    cell_loc={}  # 记录每个id栅格的位置，下一步追溯下游流向
    final_id=max(ids[ids!=-9999])


    # 需要再加一步，去处理高差过大的HRU。原理：根据已经处理好的河网，去回溯上游进行拆分
    max_final_id = 0
    for stream_id in Stream_dic:
        cells = Stream_dic[stream_id]
        while cells:
            pop_cell = cells.pop()
            upstreams = util_ZB.get_rever_D8(Dir, pop_cell[0], pop_cell[1])
            for cell in upstreams:
                if Stream[cell[0], cell[1]] == streamnodata:
                    ids[cell[0], cell[1]] += final_id
                    max_final_id = max(max_final_id, ids[cell[0], cell[1]])
                    cells.append((cell))
        final_id = max_final_id
    # Raster.save_raster(os.path.join(Basin_dir, 'HRU_2' + Basin_id + '.tif'), ids, proj,
    #                    geo, gdal.GDT_Float32, -9999)
    # 拆分
    # final_id = 0
    for i in range(row):
        for j in range(col):
            if vis[i, j] == 0 and ids[i, j] != -9999:
                # 开始寻找
                pop_cells = [(i, j)]
                vis, res = util_ZB.bfs(ids[i, j], i, j, ids, vis)
                # cell_loc.setdefault(final_id, res)

                for cell in res:
                    ids[cell[0], cell[1]] = final_id
                final_id += 1

    # Raster.save_raster(os.path.join(Basin_dir, 'HRU_3' + Basin_id + '.tif'), ids, proj,
    #                    geo, gdal.GDT_Float32, -9999)
    # 这一步做最终的合并，将小于阈值的斑块进行拆分：迭代合并至最近集合，因为此时各斑块没有流向关系
    HRU_ids=np.unique(ids[ids!=-9999])
    for HRU_id in HRU_ids:
        num=len(ids[ids==HRU_id])
        if num<11:   # 最小阈值
            # 合并至上游
            locs=np.argwhere(ids==HRU_id)
            wait_id=-1
            ff=False
            for cell in locs:
                for i in range(8):
                    next_cell=(cell[0]+dmove[i][0],cell[1]+dmove[i][1])
                    if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                        if ids[next_cell[0],next_cell[1]]!=HRU_id and Stream[next_cell[0],next_cell[1]]==streamnodata and ids[next_cell[0],next_cell[1]]!=-9999:
                            wait_id=ids[next_cell[0],next_cell[1]]
                            ff=True
                            break
                if ff:
                    break
            # 将这个集合合并至目标集合
            # print('*****************************************************',wait_id)
            for cell in locs:
                ids[cell[0],cell[1]]=wait_id

    # Raster.save_raster(os.path.join(Basin_dir, 'HRU_1' + Basin_id + '.tif'), ids, proj,
    #                    geo, gdal.GDT_Float32, -9999)

    final_id=0
    vis = np.zeros_like(result_arr)
    for i in range(row):
        for j in range(col):
            if vis[i,j]==0 and ids[i,j]!=-9999:
                # 开始寻找
                # pop_cells=[(i,j)]
                vis,res=util_ZB.bfs(ids[i,j],i,j,ids,vis)
                cell_loc.setdefault(final_id,res)

                for cell in res:
                    result_arr[cell[0],cell[1]]=final_id
                final_id+=1





    # 记录HRU之间的流向
    downstream_dic={}
    for HRU_id in cell_loc:
        cells=cell_loc[HRU_id]
        downstream_id=set()
        for cell in cells:
            cell_dir=Dir[cell[0],cell[1]]
            if cell_dir in dmove_dic:
                next_cell=(cell[0]+dmove_dic[cell_dir][0],cell[1]+dmove_dic[cell_dir][1])
                if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                    next_id=result_arr[next_cell[0],next_cell[1]]
                    if next_id!=HRU_id :
                        if next_id==-9999:
                            downstream_id.add(-1)
                            break
                        if Stream[next_cell[0],next_cell[1]]!=streamnodata:
                            downstream_id.add(-1)
                            break
                        else:
                            downstream_id.add(int(next_id))
                            break
        downstream_dic.setdefault(HRU_id,list(downstream_id))
    # print(downstream_dic)
    # if len()
    # 写入txt
    fields_file=os.path.join(Basin_dir, 'fields_' + Basin_id +'_0' + '.txt')
    Note = open(fields_file, mode='w')
    info=['FID    downstreamFID    subbasin\n']
    for HRU_id in downstream_dic:
        if len(downstream_dic[HRU_id])!=0:

            info.append(str(HRU_id)+'    '+str(downstream_dic[HRU_id][0])+'    '+str(Basin_id)+'\n')
    Note.writelines(info)
    Note.close()




    Raster.save_raster(os.path.join(Basin_dir, 'HRU' + Basin_id + '.tif'), result_arr, proj,
                       geo, gdal.GDT_Float32, -9999)

    result_arr[result_arr!=-9999]=1
    Raster.save_raster(os.path.join(Basin_dir, 'Subbasin' + Basin_id + '.tif'), result_arr, proj,
                       geo, gdal.GDT_Float32, -9999)


    # OPTICS

def Divide_By_HRU(venu,Lu_file,DEM_file,Basin_id,Soil_file=None,Area_thresold=100):
    """
    根据土地利用数据和高程划分。
    思路：

    Add:判断是否为平原区，参考 ”坡面与子流域“ 的方法。是平原区则叠加土地利用和土壤；否则进行 2）
    2）在每个坡面上划分高程带，设定阈值band_num；
    3）叠加土地利用
    4）拆分不连续像元；
    5）合并较小像元至临近集合。


    :param Lu_file:土地利用数据
    :param DEM_file:
    :param Soil_file:土壤数据
    :return:
    """
    # Basin_id=os.path.(DEM_file)
    # print(Basin_id)
    Out_PATH=os.path.join(venu,'HLU',str(Basin_id))
    if not os.path.exists(os.path.join(venu,'HLU')):
        os.mkdir(os.path.join(venu,'HLU'))
    if not os.path.exists(Out_PATH):
        os.mkdir(Out_PATH)
    out_file=os.path.join(Out_PATH,'HLU'+str(Basin_id)+'.tif')
    # print(out_file)
    DEM=Raster.get_raster(DEM_file)
    proj,geo,DEM_nodata=Raster.get_proj_geo_nodata(DEM_file)
    LU=Raster.get_raster(Lu_file)
    _,_,LU_nodata=Raster.get_proj_geo_nodata(Lu_file)
    if Soil_file!=None:
        Soil=Raster.get_raster(Soil_file)
        _,_,Soil_nodata=Raster.get_proj_geo_nodata(Soil_file)
    row,col=DEM.shape

    # 计算高差，小于100m的直接叠加土地利用和土壤
    Max_H=DEM[DEM!=DEM_nodata].max()
    Min_H = DEM[DEM != DEM_nodata].min()
    dH=Max_H-Min_H

    if dH<100 and Soil_file!=None:
        HLU=np.zeros((row,col))
        HLU[:,:]=-9999
        for i in range(row):
            for j in range(col):
                if LU[i,j]!=LU_nodata and Soil[i,j]!=Soil_nodata:
                    HLU[i,j]=LU[i,j]+Soil[i,j]
        # HLU[LU==LU_nodata]=-9999
        # 拆分不连续的像元
        id_cells1 = {}     # 构建字典，存储每个id的栅格，{id:[cell...]}，合并规则：从指定阈值Area_thresold开始，先从最小的开始，有大的就合并到大的，没有就相邻最大的，再更新HLU和字典
        Vis=np.zeros((row,col))
        id=HLU[HLU!=-9999].max()+1
        # print('1')
        for i in range(row):
            for j in range(col):
                if DEM[i,j]!= DEM_nodata and Vis[i,j]==0 :
                    # print(i,j)
                    Vis,collections=util_ZB.bfs(HLU[i,j],i,j,HLU,Vis)
                    id_cells1.setdefault(id,collections)
                    for cell in collections:
                        HLU[cell[0],cell[1]]=id
                    id+=1

        # Raster.save_raster(r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\石羊河\DATA\A0.tif', HLU, proj, geo,
        #                    gdal.GDT_Float32, -9999)
        #
        # print(id_cells1)
        for HLU_id in id_cells1:
            cells=id_cells1[HLU_id].copy()
            if len(cells)<=Area_thresold:
                # 合并
                while cells:
                    pop_cell=cells.pop()
                    if HLU[pop_cell[0],pop_cell[1]]==HLU_id:
                        continue
                    if len(id_cells1[HLU[pop_cell[0],pop_cell[1]]])>Area_thresold:
                        # 合并
                        HLU[HLU==HLU_id]=HLU[pop_cell[0],pop_cell[1]]
                        # for cell in id_cells1[HLU_id]:
                        #     HLU[cell[0],cell[1]]=HLU[pop_cell[0],pop_cell[1]]
                        break
                    for k in range(8):
                        next_cell=(pop_cell[0]+dmove[k][0],pop_cell[1]+dmove[k][1])
                        if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                            if HLU[next_cell[0],next_cell[1]] not in [-9999,HLU_id] :
                                cells.append(next_cell)

        # HLU[Soil==Soil_nodata]=-9999
        # Raster.save_raster(r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\石羊河\DATA\A.tif',HLU,proj,geo,gdal.GDT_Float32,-9999)
    if dH>=100 or Soil_file==None:
        # "自然断点法划高程带,6带"
        # print('1')
        HLU = np.zeros((row, col))
        HLU[:, :] = -9999
        DEMs=DEM[DEM!=DEM_nodata]
        DEM_cells=np.argwhere(DEM!=DEM_nodata)
        breaks=jenkspy.jenks_breaks(DEMs,6)
        i=6
        while i>=0:
            for cell in DEM_cells:
                if DEM[cell[0],cell[1]]<math.ceil(breaks[i]):
                    HLU[cell[0],cell[1]]=i
                    # print(HLU[cell[0],cell[1]])
            i-=1

        # id=3
        for i in range(row):
            for j in range(col):
                if LU[i,j]!=LU_nodata and DEM[i,j]!=DEM_nodata:
                    HLU[i,j]+=LU[i,j]

        # 拆分不连续单元
        Max_id=HLU[HLU!=-9999].max()
        A=Max_id.copy()
        Vis=np.zeros((row,col))
        for i in range(row):
            for j in range(col):
                if Vis[i,j]==0 and DEM[i,j]!=DEM_nodata and HLU[i,j]!=-9999:
                    Vis,collections=util_ZB.bfs(HLU[i,j],i,j,HLU,Vis)
                    for cell in collections:
                        HLU[cell[0],cell[1]]=Max_id
                    Max_id+=1
        HLU[LU==LU_nodata]=-9999
        # HLU-=A
        # HLU[HLU<-1]=-9999
        # HLU=median_filter(HLU,5)

        # 合并到周围
        Vis_1=np.zeros((row,col))
        for i in range(row):
            for j in range(col):
                if HLU[i,j]!=-9999 and Vis_1[i,j]==0:
                    Vis_1,ollections=util_ZB.bfs(HLU[i,j],i,j,HLU,Vis_1)
                    if len(collections)<=10:
                        # 合并
                        new_id=HLU[i,j]
                        Vis_2 = np.zeros((row, col))
                        while collections:
                            pop_cell=collections.pop()
                            for k in range(8):
                                next_cell=(pop_cell[0]+dmove[k][0],pop_cell[1]+dmove[k][1])
                                if 0<=next_cell[0]<row and 0<=next_cell[1]<col:
                                    if HLU[next_cell[0],next_cell[1]]!=-9999 and HLU[next_cell[0],next_cell[1]]!=HLU[i,j]:
                                        new_id=HLU[next_cell[0],next_cell[1]]
                                        break
                                    if Vis_2[next_cell[0],next_cell[1]]==0:
                                        collections.insert(0,next_cell)
                                        Vis_2[next_cell[0], next_cell[1]] = 1
                        for cell in collections:
                            HLU[cell[0],cell[1]]=new_id
        Raster.save_raster(out_file,HLU,proj,geo,gdal.GDT_Float32,-9999)

def median_filter(image, kernel_size):
    # 获得图像的大小
    height, width = image.shape

    # 获得中值滤波器的半径
    radius = kernel_size // 2

    # 创建一个与原图像大小相同的空白图像
    filtered_image = np.zeros_like(image)

    # 遍历原图像的每一个像素
    for i in range(height):
        for j in range(width):
            # 获得滤波器内的像素值
            neighbors = []
            for k in range(-radius, radius + 1):
                for l in range(-radius, radius + 1):
                    # 边界检查
                    if i + k >= 0 and i + k < height and j + l >= 0 and j + l < width:
                        neighbors.append(image[i + k, j + l])

            # 对滤波器内的像素值进行排序并取中间值作为当前像素的值
            neighbors.sort()
            filtered_image[i, j] = neighbors[len(neighbors) // 2]

    return filtered_image

def merge_HLU(venu):
    """
    针对小流域的合并，Clip.customline=False时使用
    :param venu:
    :return:
    """
    HLU_path = os.path.join(venu, 'HLU')
    Basin_dir = os.listdir(HLU_path)
    HLU_files = [os.path.join(HLU_path, Basin, 'HLU' + Basin + '.tif') for Basin in Basin_dir]
    fields_files = [os.path.join(HLU_path, Basin, 'fields_') + Basin + '_0' + '.txt' for Basin in Basin_dir]
    id=0
    final_HRU_downstream=['FID    downstreamFID    subbasin\n']
    for k, HLU_file in enumerate(HLU_files):
        Subbasin_id=os.path.basename(HLU_file).split('.')[0][3:]
        HRU = Raster.get_raster(HLU_file)
        row, col = HRU.shape
        if id == 0:
            proj, geo, nodata = Raster.get_proj_geo_nodata(HLU_file)
            res = np.zeros((row, col), int)
            res[:, :] = -9999
        flags = np.unique(HRU)
        # print(HRU_file,flags)
        for flag in flags:
            if flag != nodata:
                # old_new_HRUid[flag] = id
                res[HRU == flag] = id
                final_HRU_downstream.append(str(id)+'    '+str(-9999)+'    '+str(Subbasin_id)+'\n')
                id += 1

    Raster.save_raster(os.path.join(venu, 'ALL_HLU_final' + '.tif'), res, proj,
                       geo, gdal.GDT_Float32, -9999)

    fields_file = os.path.join(venu, 'ALL_HLU_fields' + '.txt')
    Note = open(fields_file, mode='w')
    info = ['FID    downstreamFID    subbasin\n']
    # for HRU_id in downstream_dic:
    #     info.append(str(HRU_id)+'    '+str(downstream_dic[HRU_id][0])+'    '+str(Basin_id)+'\n')

    Note.writelines(final_HRU_downstream)
    Note.close()

def merge_HRU(venu):
    """
    针对小流域的合并，Clip.customline=False时使用
    :param venu:
    :return:
    """
    HRU_path=os.path.join(venu,'HRU')
    Basin_dir=os.listdir(HRU_path)
    HRU_files=[os.path.join(HRU_path,Basin,'HRU'+Basin+'.tif') for Basin in Basin_dir]
    fields_files=[os.path.join(HRU_path,Basin,'fields_')+Basin+'_0'+'.txt' for Basin in Basin_dir]

    id=0
    final_HRU_downstream=['FID    downstreamFID    subbasin\n']
    for k,HRU_file in enumerate(HRU_files):
        old_new_HRUid = {}  # 记录旧id和新id的对应关系，生成新的HRU流向表
        f=open(fields_files[k])
        con=f.readlines()[1:]
        # print(con.split('    '))
        # print(con)
        HRU=Raster.get_raster(HRU_file)
        row,col=HRU.shape
        if id==0:
            proj,geo,nodata=Raster.get_proj_geo_nodata(HRU_file)
            res=np.zeros((row,col),int)
            res[:,:]=-9999
        flags=np.unique(HRU)
        # print(HRU_file,flags)
        for flag in flags:
            if flag!=nodata:
                old_new_HRUid[flag]=id
                res[HRU==flag]=id
                id+=1
        # print(old_new_HRUid)
        # 更换新id到HRU流向文件
        # print(con)
        for info in con:
            new_info=info.split('    ')
            # print(new_info)
            x=[]
            for num,c in enumerate(new_info):

                if int(c) in old_new_HRUid:
                    if num<2:
                        x.append(str(old_new_HRUid[int(c)]))
                    else:
                        x.append(str(c))
                else:
                    x.append(c)
            # print(x)
            # print('x','    '.join(x))
            final_HRU_downstream.append('    '.join(x))

        # print(con)
    Raster.save_raster(os.path.join(venu, 'ALL_HRU_final' + '.tif'), res, proj,
                       geo, gdal.GDT_Float32, -9999)
    # print(final_HRU_downstream)
    print('开始写入流向文件')
    # # 写入txt
    fields_file=os.path.join(venu, 'ALL_HRU_fields' + '.txt')
    Note = open(fields_file, mode='w')
    info=['FID    downstreamFID    subbasin\n']
    # for HRU_id in downstream_dic:
    #     info.append(str(HRU_id)+'    '+str(downstream_dic[HRU_id][0])+'    '+str(Basin_id)+'\n')
    Note.writelines(final_HRU_downstream)
    Note.close()
    print('成功写入流向文件')

def merge_patch(venu):
    """
    针对小流域的合并，Clip.customline=False时使用
    :param venu:
    :return:
    """
    HRU_path=os.path.join(venu,'HRU')
    Basin_dir=os.listdir(HRU_path)
    Basin_dir=[os.path.join(HRU_path,Basin,'process_patch1'+Basin+'.tif') for Basin in Basin_dir]

    id=1
    for HRU_file in Basin_dir:

        HRU=Raster.get_raster(HRU_file)
        row,col=HRU.shape
        if id==1:
            proj,geo,nodata=Raster.get_proj_geo_nodata(HRU_file)
            res=np.zeros((row,col),int)
            res[:,:]=-9999
        flags=np.unique(HRU)
        # print(HRU_file,flags)
        for flag in flags:
            if flag!=nodata:
                res[HRU==flag]=id
                id+=1
    Raster.save_raster(os.path.join(venu, 'ALL_process_Patch1' + '.tif'), res, proj,
                       geo, gdal.GDT_Float32, -9999)

if __name__=='__main__':

    # *******************TestBasin模拟***********************
    # venu = r'E:\空间离散化\小流域测试\XJS'
    # Stream_file=r'E:\空间离散化\小流域测试\XJS\Stream1.tif'
    # Dir_file=r'E:\空间离散化\小流域测试\XJS\Dir_1.tif'
    # # out_file=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Test_Basin2\new_discretize3.tif'
    # # LU_file=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Test_Basin2\LU.tif'
    # # Slope_file=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Test_Basin2\Slope.tif'
    # # HAND_file=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\Test_Basin2\HillSlope\HillSlope\412100127606\HAND412100127606.tif'
    # Divde_Lake_HillSlope(venu,Dir_file,Stream_file,LU_file,Slope_file,HAND_file)
    # # merge_HRU(venu)
    # # merge_patch(venu)
    #
    # # ****************葫芦沟20240203合并*********************
    # venu = r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\HLU20240203'
    # merge_HRU(venu)
    # # merge_patch(venu)


    # *********** Stteper 代码测试 *************

    LU = r'E:\空间离散化\小流域测试\Stteper\landuse.tif'
    DEM = r'E:\空间离散化\小流域测试\Stteper\basin_elv.tif'
    Soil = r''
    out_file = r'E:\空间离散化\小流域测试\Stteper\Stteper_LU_DEM_HRU.tif'
    #
    Divide_By_HRU(LU, DEM, out_file)


    # ************ 葫芦沟HRU划分数据_0227 空间离散化测试 **************

    LU=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\HRU划分数据_0227\landuse.tif'
    DEM=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\HRU划分数据_0227\HRU划分数据\dem.tif'
    Soil=r''
    out_file=r'E:\青藏高原东部河流输出碳\DATA\SubBasin_singleSHP\HRU划分数据_0227\LU_DEM_HRU_6.tif'

    # Divide_By_HRU(LU,DEM,out_file)

    pass