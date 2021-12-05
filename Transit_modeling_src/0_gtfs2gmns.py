# -*- coding: utf-8 -*-
import copy
import os
import math
import datetime
import numpy as np
import pandas as pd
import time

def split_ignore_separators_in_quoted(s, separator=',', quote_mark='"'):
    result = []
    quoted = False
    current = ''
    for i in range(len(s)):
        if quoted:
            current += s[i]
            if s[i] == quote_mark:
                quoted = False
            continue
        if s[i] == separator:
            result.append(current.strip())
            current = ''
        else:
            current += s[i]
            if s[i] == quote_mark:
                quoted = True
    result.append(current)
    return result
 
def readtxt(filename):
    Filepath = filename +'.txt'
    data = []
    with open(Filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        first_line = lines[0].split('\n')[0].split(',')
        for line in lines:
            if len(line.split('\n')[0].split(',')) == len(first_line):
                data.append(line.split('\n')[0].split(','))
            else:
                data.append(split_ignore_separators_in_quoted(line))
    df_data = pd.DataFrame(data[1:], columns=data[0])
    return df_data


def LLs2Dist(lon1, lat1, lon2, lat2): #WGS84 transfer coordinate system to distance(mile) #xy
    R = 6371
    dLat = (lat2 - lat1) * math.pi / 180.0
    dLon = (lon2 - lon1) * math.pi / 180.0

    a = math.sin(dLat / 2) * math.sin(dLat/2) + math.cos(lat1 * math.pi / 180.0) * math.cos(lat2 * math.pi / 180.0) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c * 1000 / 1609 # 1mile = 1609 meter
    return distance


def convert_gmns(gtfs_path, gmns_path, NUM, num_of_agency):
    
    time_period_id = [1] 
    
    time_period_1 = '0700_0800'
    from_time_1 = datetime.time(int(time_period_1[0:2]), int(time_period_1[2:4]))
    to_time_1 = datetime.time(int(time_period_1[-4:-2]), int(time_period_1[-2:]))
    from_time_min_1 = from_time_1.hour * 60 + from_time_1.minute
    to_time_min_1 = to_time_1.hour * 60 + to_time_1.minute
    
    from_time_min = [from_time_min_1]
    to_time_min = [to_time_min_1]
    time_period_num = len(time_period_id) # 1
    print('Time period:',time_period_num)


    '''1. READ FILES'''
    #1.1 Initialized
    # start_time = time.time()
    m_PT_StopMap = readtxt(gtfs_path + os.sep + 'stops')
    m_PT_RouteMap = readtxt(gtfs_path + os.sep + 'routes')
    m_PT_TripMap = readtxt(gtfs_path + os.sep + 'trips')
    TransitStopTime = readtxt(gtfs_path + os.sep + 'stop_times')
    m_PT_Agency = readtxt(gtfs_path + os.sep + 'agency')
    

    if 'direction_id' not in m_PT_TripMap.columns.tolist():
        m_PT_TripMap['direction_id'] = str(0)

    agency_name = m_PT_Agency['agency_name'][0]
    if '"' in agency_name:
        agency_name = eval(agency_name)


    m_PT_TripMap['direction_id'] = m_PT_TripMap.apply(lambda x: str( 2 - int(x['direction_id'])), axis = 1)

    #1.2
    m_PT_TripMap_directed_route_id = m_PT_TripMap['route_id'].astype(str).str.cat(m_PT_TripMap['direction_id'].astype(str), sep='.')
    m_PT_TripMap['directed_route_id'] = m_PT_TripMap_directed_route_id

    # Nov 10: To fix the bug dealing with Agency 12 Fairfax CUE
    if (m_PT_RouteMap['route_id'][0][0] == '"') != (m_PT_TripMap['route_id'][0][0] == '"'):
        if m_PT_RouteMap['route_id'][0][0] == '"':
            m_PT_RouteMap['route_id'] = m_PT_RouteMap.apply(lambda x: x['route_id'].strip('"'), axis=1)
        else:
            m_PT_TripMap['route_id'] = m_PT_TripMap.apply(lambda x: x['route_id'].strip('"'), axis=1)


    m_PT_RouteTripMap = pd.merge(m_PT_TripMap, m_PT_RouteMap, on='route_id') # Goes Wrong in Agency 12
    m_PT_DirectedRouteStopMap = pd.merge(m_PT_RouteTripMap,TransitStopTime,on='trip_id')
    m_PT_DirectedRouteStopMap_directed_route_stop_id = m_PT_DirectedRouteStopMap['directed_route_id'].astype(str).str.cat(m_PT_DirectedRouteStopMap['stop_id'].astype(str), sep='.')
    m_PT_DirectedRouteStopMap['directed_route_stop_id'] = m_PT_DirectedRouteStopMap_directed_route_stop_id
    
    
    '''2. NODE'''
    #2.1 physical node
    node_csv = pd.DataFrame()
    
    ##2.1.1 stop_id
    df_m_PT_Direct = m_PT_DirectedRouteStopMap[['stop_id','directed_route_stop_id','directed_route_id','stop_sequence','route_type']]
    df_m_PT_StopMap = m_PT_StopMap[['stop_id','stop_lat','stop_lon']]
    df_merge_StopMap = pd.merge(df_m_PT_Direct, df_m_PT_StopMap, on='stop_id').drop_duplicates(subset=['stop_id'])

    # # df_m_PT_Direct_termimal = pd.merge(df_m_PT_Direct.copy(),node_csv.copy().reset_index()[['node_id', 'name']],left_on='stop_id', right_on='name', how='left')
    #
    df_m_PT_Direct_termimal = df_m_PT_Direct[['stop_id','directed_route_id','stop_sequence']]


    df_m_PT_Direct_termimal['int_stop_sequence'] = df_m_PT_Direct_termimal.apply(lambda x : int(x['stop_sequence']), axis=1)




    dict_terminal = pd.DataFrame()
    dict_terminal['directed_route_id'] = df_m_PT_Direct_termimal['directed_route_id'].unique()
    dict_terminal['min'] = dict_terminal.apply(lambda x : df_m_PT_Direct_termimal[
        df_m_PT_Direct_termimal['directed_route_id']==x['directed_route_id']]['int_stop_sequence'].min(), axis=1)
    dict_terminal['max'] = dict_terminal.apply(lambda x : df_m_PT_Direct_termimal[
        df_m_PT_Direct_termimal['directed_route_id']==x['directed_route_id']]['int_stop_sequence'].max(), axis=1)

    dt = dict_terminal.set_index(['directed_route_id']).to_dict()


    df_m_PT_Direct_termimal['terminal_flag'] = df_m_PT_Direct_termimal.apply(
        lambda x:
        (x['int_stop_sequence'] == dt['max'][x['directed_route_id']]) |
        (x['int_stop_sequence'] == dt['min'][x['directed_route_id']])
    ,axis=1)


    stops_terminal = pd.pivot_table(df_m_PT_Direct_termimal, index=['stop_id'],values=['terminal_flag'],aggfunc=np.max)
    stops_terminal.index.name = 'name'
    print()

    #
    # gp = df_m_PT_Direct_termimal.groupby('directed_route_id')
    #
    # dataList_stop = {}
    # for key, form in gp:
    #
    #     dataList_stop[key] = {
    #         'stop_id': form['stop_id'].iloc[0],
    #         'directed_route_id_sequence': form['directed_route_id'].tolist(),
    #         'stop_sequence_sequence': form['stop_sequence'].tolist()
    #     }
    #
    #     active_route_sequence_size = len(dataList_stop[key]['directed_route_id_sequence'])
    #     active_stop_sequence_size = len(dataList_stop[key]['stop_sequence_sequence'])
    #
    #     for i in range(active_route_sequence_size - 1):
    #         for j in range(active_stop_sequence_size - 1):
    #             max_sequence = max(dataList_stop[key]['stop_sequence_sequence'][j])
    #         if dataList_stop[key]['stop_sequence_sequence'] == 1:
    #             node_csv['terminal_flag'] = 1
    #         elif dataList_stop[key]['stop_sequence_sequence'] == int(max_sequence):
    #             node_csv['terminal_flag'] = 1
    #         else:
    #             node_csv['terminal_flag'] = ' '



    ##2.1.2 physical node
    node_csv['name'] = df_merge_StopMap['stop_id']
    node_csv['x_coord'] = df_merge_StopMap['stop_lon']
    node_csv['y_coord'] = df_merge_StopMap['stop_lat']
    node_csv['node_type'] = 'stop'
    # node_csv['terminal_flag'] = df_m_PT_Direct_termimal['terminal_flag']

    node_csv = node_csv.join(stops_terminal, on='name', how='outer')

    node_csv['directed_route_id'] = None
    node_csv['ctrl_type'] = None
    node_csv['zone_id'] = 0
    node_csv['production'] = 0.00
    node_csv['attraction'] = 0.00
    node_csv['agency_name'] = agency_name
    node_csv['geometry'] = 'POINT (' + df_merge_StopMap['stop_lon'] + ' ' + df_merge_StopMap['stop_lat'] +')'
    
    ##2.1.3 Index
    node_csv = node_csv.sort_values(by=['name'])
    node_csv.index = pd.RangeIndex(len(node_csv.index))
    node_csv.index.name = 'node_id'
    node_csv.index += int('{}00001'.format(NUM))
    
    #2.2 route stop node
    route_stop_csv = pd.DataFrame()
    
    ##2.2.1 directed_route_stop_id.drop()
    df_merge_StopMap = pd.merge(df_m_PT_Direct,df_m_PT_StopMap, on='stop_id').drop_duplicates(subset=['directed_route_stop_id'])
    
    ##2.2.2 route stop node
    route_stop_csv['name'] = df_merge_StopMap['directed_route_stop_id']
    route_stop_csv['x_coord'] = df_merge_StopMap['stop_lon'].astype(float)-0.000100
    route_stop_csv['y_coord'] = df_merge_StopMap['stop_lat'].astype(float)-0.000100
    route_stop_csv['node_type'] = 'directed_route_stop'
    # node_csv['terminal_flag'] = ' '
    route_stop_csv['directed_route_id'] = df_merge_StopMap['directed_route_id'].astype(str)
    route_stop_csv['ctrl_type'] = None
    route_stop_csv['zone_id'] = 0
    route_stop_csv['production'] = 0.00
    route_stop_csv['attraction'] = 0.00
    route_stop_csv['agency_name'] = agency_name
    route_stop_csv['geometry'] = 'POINT (' + df_merge_StopMap['stop_lon'] + ' ' + df_merge_StopMap['stop_lat'] +')'
    
    ##2.2.3 Index
    route_stop_csv = route_stop_csv.sort_values(by=['name'])
    route_stop_csv.index = pd.RangeIndex(len(route_stop_csv.index))
    route_stop_csv.index.name = 'node_id'
    route_stop_csv.index += int('{}0000001'.format(NUM))
    
    #2.3 merge node
    Node_df = pd.concat([node_csv,route_stop_csv])
    Node_df_order = ['name','x_coord','y_coord','node_type','terminal_flag','directed_route_id',
                     'ctrl_type','zone_id','production','attraction','agency_name','geometry']
    Node_df = Node_df[Node_df_order]
    # Node_df.to_csv('transit_agency_{}_node.csv'.format(NUM))
    #
    # if NUM == 1:
    #     Node_df.to_csv('combined_node.csv', sep=",")
    # else:
    #     Node_df.to_csv('combined_node.csv', mode='a+', header=False, sep=",")
    # print('Node: run time -->',time.time()-start_time)
    
    
    '''3. LINK'''
    #3.1 dict
    #3.1.1 service link
    df_PT_DirectedRouteStopMap = m_PT_DirectedRouteStopMap[['stop_id','directed_route_stop_id','route_id','trip_id','arrival_time','departure_time','stop_sequence','route_type']].copy()
    # df_PT_DirectedRouteStopMap = df_PT_DirectedRouteStopMap.dropna(axis=0, subset=['arrival_time'])
    
    def time_convert(in_str):
        hour = int(in_str[:-6])
        return str(hour % 24)+in_str[-6:]

    
    df_PT_DirectedRouteStopMap['arrival_time'] = df_PT_DirectedRouteStopMap['arrival_time'].apply(lambda x: np.NaN if x == ' ' else x)
    df_PT_DirectedRouteStopMap['arrival_time'] = df_PT_DirectedRouteStopMap['arrival_time'].apply(lambda x: np.NaN if x == '' else x)

    df_PT_DirectedRouteStopMap['departure_time'] = df_PT_DirectedRouteStopMap['departure_time'].apply(lambda x: np.NaN if x == ' ' else x)
    df_PT_DirectedRouteStopMap['departure_time'] = df_PT_DirectedRouteStopMap['departure_time'].apply(lambda x: np.NaN if x == '' else x)

    
    conv_arr_time_series = df_PT_DirectedRouteStopMap['arrival_time'].dropna().apply(lambda x: time_convert(str(x)))
    conv_dep_time_series = df_PT_DirectedRouteStopMap['departure_time'].dropna().apply(lambda x: time_convert(str(x)))
    df_PT_DirectedRouteStopMap['arrival_time_min'] = pd.to_datetime(pd.Series(conv_arr_time_series)).apply(lambda x: x.hour*60 + x.minute)
    df_PT_DirectedRouteStopMap['departure_time_min'] = pd.to_datetime(pd.Series(conv_dep_time_series)).apply(lambda x: x.hour*60 + x.minute)
    
    
    df_PT_DirectedRouteStopMap_service = pd.merge(df_PT_DirectedRouteStopMap.copy(),route_stop_csv.copy().reset_index()[['node_id','name']],left_on='directed_route_stop_id',right_on='name',how='left')
    gp = df_PT_DirectedRouteStopMap_service.groupby('trip_id')
    dataList_trip = {}
    def convert_time_sequence(time_sequence): #change format: 13:22:00 --> 1322:00
        time = []
        for i in np.unique(time_sequence):
            i=i.replace(':', '', 1)
            time.append(i)
        return time
    
    for key, form in gp: # trip 14482330
    
        List = []
        for ids in time_period_id:
            ids = ids-1
            form_temp = form[(form['arrival_time_min']>=from_time_min[ids]) & (form['arrival_time_min']<to_time_min[ids])]
            List.append(form_temp)
        form = pd.concat(List)
        if form.empty:
            continue
    
        temp = form['arrival_time_min'].dropna()
        temp = temp.reset_index()
        temp = temp['arrival_time_min']
        # temp = convert_time_sequence(temp)
        dataList_trip[key] = {
            'route_id': form['route_id'].iloc[0],
            'route_stop_id_sequence': form['directed_route_stop_id'].tolist(),
            'arrival_time_min_sequence':form['arrival_time_min'].tolist(),
            'node_id_sequence':form['node_id'].tolist(),
            'time_sequence':temp,
            'route_type_sequence':form['route_type'].tolist()
            # 'departure_time_min_sequence':form['departure_time_min'].tolist()
            }
    
    #3.1.2 vdf
    gp = df_PT_DirectedRouteStopMap_service.groupby('route_id')
    # gp = df_PT_DirectedRouteStopMap_service[df_PT_DirectedRouteStopMap_service['directed_route_stop_id']=='104.1.9442']
    
    dataList_route_stop = {}
    for key, form in gp: # route GUS1
        form = form.set_index('directed_route_stop_id')
        temp = form['arrival_time_min']
    
        # temp = temp.apply(lambda x: np.NaN if x == '' else x)
        # temp = temp.dropna() 
    
        for route_stop in temp.index.unique().tolist():
            # print(route_stop) # ZOOM.1.9252
            temp_count = [0 for x in range(len(time_period_id))]
            for ids in time_period_id:
                # a = temp[route_stop]
                ids = ids-1
                temp_node_df = pd.DataFrame(pd.Series(temp[route_stop]).rename('arrival_time_min'))
                temp_count_df = temp_node_df.groupby(temp_node_df.arrival_time_min.map(lambda x: x>=from_time_min[ids] and x<to_time_min[ids])).count()
                delta_time = list(map(lambda x: x[0]-x[1], zip(to_time_min, from_time_min)))
                if True in temp_count_df.index:
                    temp_count[ids] = temp_count_df.loc[True,:]['arrival_time_min']
    
            dataList_route_stop[route_stop] = {
                'delta_time':delta_time,
                'freq':temp_count
                }
    
    #3.1.2 physical link
    df_PT_DirectedRouteStopMap_physical = pd.merge(df_PT_DirectedRouteStopMap.copy(),node_csv.copy().reset_index()[['node_id','name']],left_on='stop_id',right_on='name',how='left')
    gp = df_PT_DirectedRouteStopMap_physical.groupby('trip_id')
    
    dataList_phy = {}
    for key, form in gp:
        # print(key)
        dataList_phy[key] = {
            'route_stop_id_sequence': form['directed_route_stop_id'].tolist(),
            'name_sequence':form['name'].tolist(),
            'node_id_sequence':form['node_id'].tolist(),
            'route_type_sequence': form['route_type'].tolist()
            }
    
    #3.2 physical link
    node_x = node_csv['x_coord']
    node_y = node_csv['y_coord']
    physical_link_list = []
    for key in dataList_phy.keys():
        # print(key) # 14486012
        active_node_sequence_size = len(dataList_phy[key]['node_id_sequence'])
    
        for i in range(active_node_sequence_size-1):
            active_from_node_id = dataList_phy[key]['node_id_sequence'][i] # 7231 node_id
            active_to_node_id = dataList_phy[key]['node_id_sequence'][i+1]
    
            active_from_node_name = dataList_phy[key]['name_sequence'][i]
            active_to_node_name = dataList_phy[key]['name_sequence'][i+1]
            active_name = active_from_node_name+'->'+active_to_node_name
    
            from_node_id_x = node_x[active_from_node_id]
            from_node_id_y = node_y[active_from_node_id]
            to_node_id_x = node_x[active_to_node_id]
            to_node_id_y = node_y[active_to_node_id]
    
            active_route_id = dataList_phy[key]['route_stop_id_sequence'][i+1][:dataList_phy[key]['route_stop_id_sequence'][i+1].rfind('.')]
    
            active_distance = LLs2Dist(float(from_node_id_x),float(from_node_id_y),float(to_node_id_x),float(to_node_id_y))
            active_fftt = active_distance / 2 * 60    # min
            active_geometry = 'LINESTRING (' + str(from_node_id_x)+' '+str(from_node_id_y)+', '+str(to_node_id_x)+' '+str(to_node_id_y)+')'

            # generate mode_type
            mode_type_name = ['tram', 'metro', 'rail', 'bus', 'ferry', 'cabletram', 'aeriallift', 'funicular', '', '', '', 'trolleybus', 'monorail']
            route_type = dataList_phy[key]['route_type_sequence'][i]
            if int(route_type) > len(mode_type_name):
                route_type_name = route_type
            else:
                route_type_name = mode_type_name[int(route_type)]

            if route_type_name == 'bus':
                allowed_use = 'w_bus;w_bus_metro;d_bus;d_bus_metro'
            elif route_type_name == 'metro':
                allowed_use = 'w_metro;w_bus_metro;d_metro;d_bus_metro'

            # delete route
            physical_link_list.append([active_name,active_from_node_id,active_to_node_id,active_route_id,active_distance,active_geometry,active_fftt,route_type_name,allowed_use])
    
    physical_link_csv = pd.DataFrame(physical_link_list, columns=['name','from_node_id','to_node_id','directed_route_id','length','geometry','VDF_fftt1','mode_type','allowed_use']).drop_duplicates(subset=['name'])
    physical_link_csv.insert(3, 'facility_type', '')
    physical_link_csv.insert(4, 'dir_flag', 1)
    physical_link_csv.insert(6, 'link_type', 1)
    physical_link_csv.insert(7, 'link_type_name', 'sta2sta_1r')
    # physical_link_csv.insert(7, 'VDF_fftt1', 0)
    physical_link_csv.insert(9, 'lanes', 1)
    physical_link_csv.insert(10, 'capacity', 5000)
    physical_link_csv.insert(11, 'free_speed', 2)
    physical_link_csv.insert(12, 'cost', 0)
    physical_link_csv.insert(14, 'VDF_cap1', 5000)
    physical_link_csv.insert(15, 'VDF_alpha1', 0.15)
    physical_link_csv.insert(16, 'VDF_beta1', 4)
    physical_link_csv.insert(17, 'VDF_theta1', 1)
    physical_link_csv.insert(18, 'VDF_gamma1', 1)
    physical_link_csv.insert(19, 'VDF_mu1', 100)
    physical_link_csv.insert(20, 'RUC_rho1', 10)
    physical_link_csv.insert(21, 'RUC_resource1', 0)
    physical_link_csv.insert(22, 'RUC_type', 1)
    physical_link_csv.insert(23, 'VDF_freq1', 24)

    # List.append(pd.DataFrame(active_distance / 5, columns=['VDF_fftt{}'.format(num + 1)]))

    physical_link_csv_order = ['name','from_node_id','to_node_id','facility_type','dir_flag','directed_route_id','link_type','link_type_name','length','lanes','capacity','free_speed','cost','VDF_fftt1','VDF_cap1','VDF_alpha1','VDF_beta1','VDF_theta1','VDF_gamma1','VDF_mu1','RUC_rho1','RUC_resource1','RUC_type','VDF_freq1','geometry','mode_type','allowed_use']
    physical_link_csv = physical_link_csv[physical_link_csv_order]
    
    
    #3.3 virtual link: physical node & route stop node
    df_merge_StopMap_NodeMap = pd.merge(df_merge_StopMap,node_csv.copy().reset_index()[['node_id','name']],left_on='stop_id',right_on='name',how='left').rename(columns={'node_id':'physical_node_id','name':'physical_name'})
    df_merge_StopMap_NodeMap = pd.merge(df_merge_StopMap_NodeMap.copy(),route_stop_csv.copy().reset_index()[['node_id','name','x_coord','y_coord']],left_on='directed_route_stop_id',right_on='name',how='left').rename(columns={'node_id':'route_stop_node_id','name':'route_stop_name'})
    
    tranfer_link_entrance_list = []
    tranfer_link_exit_list = []
    vdf_fftt_List = []
    vdf_freq_List = []
    # vdf_time_List = []
    df_merge_StopMap_NodeMap = df_merge_StopMap_NodeMap.sort_values(by=['directed_route_stop_id'])
    for index, row in df_merge_StopMap_NodeMap.iterrows():
        ative_directed_route_id = row.directed_route_id
        active_route_stop_name = row.directed_route_stop_id
        active_route_stop_node_id = row.route_stop_node_id
        active_physical_node_id = row.physical_node_id
        active_distance = LLs2Dist(float(row.stop_lon),float(row.stop_lat),float(row.x_coord),float(row.y_coord))
        active_geometry_entrance = 'LINESTRING (' + str(row.stop_lon)+' '+str(row.stop_lat)+', '+str(row.x_coord)+' '+str(row.y_coord)+')'
        active_geometry_exit = 'LINESTRING (' + str(row.x_coord)+' '+str(row.y_coord)+', '+str(row.stop_lon)+' '+str(row.stop_lat)+')'
        # route_type_name = 'walk'

        # generate mode_type
        mode_type_name = ['tram', 'metro', 'rail', 'bus', 'ferry', 'cabletram', 'aeriallift', 'funicular', '', '', '', 'trolleybus', 'monorail']
        route_type = row.route_type
        if int(route_type) > len(mode_type_name):
            route_type_name = route_type
        else:
            route_type_name = mode_type_name[int(route_type)]

        if route_type_name == 'bus':
            allowed_use = 'w_bus;w_bus_metro;d_bus;d_bus_metro'
        elif route_type_name == 'metro':
            allowed_use = 'w_metro;w_bus_metro;d_metro;d_bus_metro'

        vdf_freq_list = dataList_route_stop[active_route_stop_name]['freq']
        vdf_time_list = dataList_route_stop[active_route_stop_name]['delta_time']
    
        vdf_fftt_list = [vdf_freq_list[i] if vdf_freq_list[i]==0 else vdf_time_list[i]/vdf_freq_list[i]/2 for i in range(len(vdf_freq_list))]
        vdf_fftt_list = [15 if x>15 else x for x in vdf_fftt_list]
        # vdf_fftt_list = list(map(lambda x: x[0]/x[1]/2, zip(vdf_time_list, vdf_freq_list)))
    
        vdf_fftt_List.append(vdf_fftt_list)
        vdf_freq_List.append(vdf_freq_list)
        # vdf_time_List.append([vdf_time_list])
        tranfer_link_entrance_list.append([active_route_stop_name+'.entrance',
                                  active_physical_node_id,active_route_stop_node_id,ative_directed_route_id,
                                  active_distance,active_geometry_entrance,route_type_name,allowed_use])
    
        tranfer_link_exit_list.append([active_route_stop_name+'.exit',
                                  active_route_stop_node_id,active_physical_node_id,ative_directed_route_id,
                                  active_distance,active_geometry_exit,route_type_name,allowed_use])
    tranfer_link_entrance_csv = pd.DataFrame(tranfer_link_entrance_list, columns=['name','from_node_id','to_node_id','directed_route_id','length','geometry','mode_type','allowed_use'])
    tranfer_link_exit_csv = pd.DataFrame(tranfer_link_exit_list, columns=['name','from_node_id','to_node_id','directed_route_id','length','geometry','mode_type','allowed_use'])
    
    
    List = []
    List_2 = []
    for num in range(time_period_num):
        vdf_fftt_List_entrance = [vdf_fftt_List[i][num] for i in range(len(vdf_fftt_List))]
        vdf_freq_List_entrance = [vdf_freq_List[i][num] for i in range(len(vdf_freq_List))]
        
        vdf_fftt_List_exit = [vdf_fftt_List[i][num] for i in range(len(vdf_fftt_List))]
        vdf_freq_List_exit = [vdf_freq_List[i][num] for i in range(len(vdf_freq_List))]
    
        List.append(pd.DataFrame(vdf_fftt_List_entrance,columns=['VDF_fftt{}'.format(num+1)]))
        List.append(pd.DataFrame([5000 for x in range(len(vdf_fftt_List_entrance))],columns=['VDF_cap{}'.format(num+1)]))
        List.append(pd.DataFrame([0.15 for x in range(len(vdf_fftt_List_entrance))],columns=['VDF_alpha{}'.format(num+1)]))
        List.append(pd.DataFrame([4 for x in range(len(vdf_fftt_List_entrance))],columns=['VDF_beta{}'.format(num+1)]))
        List.append(pd.DataFrame(vdf_freq_List_entrance,columns=['VDF_freq{}'.format(num+1)]))
    
        # tranfer_link_exit_csv['VDF_fftt{}'.format(num+1)] = 2
        # tranfer_link_exit_csv['VDF_cap{}'.format(num+1)] = 10000
        # tranfer_link_exit_csv['VDF_alpha{}'.format(num+1)] = 0.15
        # tranfer_link_exit_csv['VDF_beta{}'.format(num+1)] = 4
        # tranfer_link_exit_csv['VDF_freq{}'.format(num+1)] = 0
        
        #List_2.append(pd.DataFrame(vdf_fftt_List_exit,columns=['VDF_fftt{}'.format(num+1)]))
        List_2.append(pd.DataFrame([0 for x in range(len(vdf_fftt_List_exit))], columns=['VDF_fftt{}'.format(num + 1)]))
        List_2.append(pd.DataFrame([10000 for x in range(len(vdf_fftt_List_exit))],columns=['VDF_cap{}'.format(num+1)]))
        List_2.append(pd.DataFrame([0.15 for x in range(len(vdf_fftt_List_exit))],columns=['VDF_alpha{}'.format(num+1)]))
        List_2.append(pd.DataFrame([4 for x in range(len(vdf_fftt_List_exit))],columns=['VDF_beta{}'.format(num+1)]))
        List_2.append(pd.DataFrame(vdf_freq_List_exit,columns=['VDF_freq{}'.format(num+1)]))
    
    vdf_entrance = pd.DataFrame()
    vdf_entrance = pd.concat(List,axis=1)
    
    vdf_exit = pd.DataFrame()
    vdf_exit = pd.concat(List_2,axis=1)
    
    tranfer_link_entrance_csv_temp = pd.concat([tranfer_link_entrance_csv,vdf_entrance],axis=1)
    tranfer_link_exit_csv_temp = pd.concat([tranfer_link_exit_csv,vdf_exit],axis=1)
    
    transfer_link_vdf_csv = pd.concat([tranfer_link_entrance_csv_temp,tranfer_link_exit_csv_temp])
    transfer_link_vdf_csv = transfer_link_vdf_csv.sort_values(by=['name'])

    transfer_link_vdf_csv.insert(3, 'facility_type', '')
    transfer_link_vdf_csv.insert(4, 'dir_flag', 1)
    transfer_link_vdf_csv.insert(6, 'link_type', 2)
    transfer_link_vdf_csv.insert(7, 'link_type_name', 'sta2r')
    # physical_link_csv.insert(7, 'VDF_fftt1', 0)
    transfer_link_vdf_csv.insert(9, 'lanes', 1)
    transfer_link_vdf_csv.insert(10, 'capacity', 5000)
    transfer_link_vdf_csv.insert(11, 'free_speed', 2)
    transfer_link_vdf_csv.insert(12, 'cost', 0)
    # transfer_link_vdf_csv.insert(14, 'VDF_cap1', 5000)
    # transfer_link_vdf_csv.insert(15, 'VDF_alpha1', 0.15)
    # transfer_link_vdf_csv.insert(16, 'VDF_beta1', 4)
    transfer_link_vdf_csv.insert(17, 'VDF_theta1', 1)
    transfer_link_vdf_csv.insert(18, 'VDF_gamma1', 1)
    transfer_link_vdf_csv.insert(19, 'VDF_mu1', 100)
    transfer_link_vdf_csv.insert(20, 'RUC_rho1', 10)
    transfer_link_vdf_csv.insert(21, 'RUC_resource1', 0)
    transfer_link_vdf_csv.insert(22, 'RUC_type', 1)

    # List.append(pd.DataFrame(active_distance / 5, columns=['VDF_fftt{}'.format(num + 1)]))

    transfer_link_vdf_csv_order = ['name','from_node_id','to_node_id','facility_type','dir_flag','directed_route_id','link_type','link_type_name','length','lanes','capacity','free_speed','cost','VDF_fftt1','VDF_cap1','VDF_alpha1','VDF_beta1','VDF_theta1','VDF_gamma1','VDF_mu1','RUC_rho1','RUC_resource1','RUC_type','VDF_freq1','geometry','mode_type','allowed_use']
    transfer_link_vdf_csv = transfer_link_vdf_csv[transfer_link_vdf_csv_order]
    
    #3.4 service link: route stop node & route stop node
    route_stop_id_name_series = pd.Series(route_stop_csv['name'].index.tolist(), index=route_stop_csv['name'].values.tolist())
    route_stop_x_series = route_stop_csv['x_coord']
    route_stop_y_series = route_stop_csv['y_coord']
    
    service_link_list = []
    vdf_freq_List = []
    vdf_time_List = []
    # df_dataList_trip = pd.DataFrame(dataList_trip).T
    for key in dataList_trip.keys():
        # key = '14485720'
        active_node_sequence_size = len(dataList_trip[key]['route_stop_id_sequence'])
        for i in range(active_node_sequence_size-1):
            active_from_route_stop_id = dataList_trip[key]['route_stop_id_sequence'][i] # 3.0.897
            active_to_route_stop_id = dataList_trip[key]['route_stop_id_sequence'][i+1]
            
            active_fftt_from = dataList_trip[key]['time_sequence'][i]
            active_fftt_to = dataList_trip[key]['time_sequence'][i+1]
            
            active_fftt = active_fftt_to - active_fftt_from

            # generate mode_type
            mode_type_name = ['tram', 'metro', 'rail', 'bus', 'ferry', 'cabletram', 'aeriallift', 'funicular', '', '', '', 'trolleybus', 'monorail']
            route_type = dataList_trip[key]['route_type_sequence'][i]
            if int(route_type) > len(mode_type_name):
                route_type_name = route_type
            else:
                route_type_name = mode_type_name[int(route_type)]

            if route_type_name == 'bus':
                allowed_use = 'w_bus;w_bus_metro;d_bus;d_bus_metro'
            elif route_type_name == 'metro':
                allowed_use = 'w_metro;w_bus_metro;d_metro;d_bus_metro'

            ative_directed_route_id = active_from_route_stop_id[:active_from_route_stop_id.rfind('.')]
            active_name = active_from_route_stop_id+'->'+active_to_route_stop_id
            active_from_route_stop_index = route_stop_id_name_series[active_from_route_stop_id]
            # active_from_route_stop_index = route_stop_id_name_series[route_stop_id_name_series.values == active_from_route_stop_id].index[0]
            active_from_route_stop_id_x = route_stop_x_series[active_from_route_stop_index]
            active_from_route_stop_id_y = route_stop_y_series[active_from_route_stop_index]
            active_to_route_stop_index = route_stop_id_name_series[active_to_route_stop_id]
            active_to_route_stop_id_x = route_stop_x_series[active_to_route_stop_index]
            active_to_route_stop_id_y = route_stop_y_series[active_to_route_stop_index]
    
            vdf_freq_list = dataList_route_stop[active_to_route_stop_id]['freq']
            vdf_time_list = dataList_route_stop[active_to_route_stop_id]['delta_time']
            vdf_fftt_list = [vdf_freq_list[i] if vdf_freq_list[i]==0 else vdf_time_list[i]/vdf_freq_list[i]/2 for i in range(len(vdf_freq_list))]
            vdf_freq_List.append(vdf_freq_list)
            vdf_time_List.append(vdf_time_list)

            active_distance = LLs2Dist(active_from_route_stop_id_x,active_from_route_stop_id_y,active_to_route_stop_id_x,active_to_route_stop_id_y)/1609 # 1mile = 1609meter
            active_geometry = 'LINESTRING (' + str(active_from_route_stop_id_x)+' '+str(active_from_route_stop_id_y)+','+str(active_to_route_stop_id_x)+' '+str(active_to_route_stop_id_y)+')'
    
            service_link_list.append([active_name,active_from_route_stop_index,active_to_route_stop_index,
                                      ative_directed_route_id,
                                      active_distance,active_fftt,active_geometry,route_type_name,allowed_use])
    service_link_csv = pd.DataFrame(service_link_list, columns=['name','from_node_id','to_node_id','directed_route_id','length','VDF_fftt{}'.format(num+1),'geometry','mode_type','allowed_use'])
    
    
    time_period_num = len(time_period_id)
    List= []
    for num in range(time_period_num):
        vdf_freq_List_service = [vdf_freq_List[i][num] for i in range(len(vdf_freq_List))]
        vdf_time_List_service = [vdf_time_List[i][num] for i in range(len(vdf_time_List))]
    
        # List.append(pd.DataFrame(vdf_time_List_service,columns=['VDF_fftt{}'.format(num+1)]))
        List.append(pd.DataFrame([5000 for x in range(len(vdf_freq_List_service))],columns=['VDF_cap{}'.format(num+1)]))
        List.append(pd.DataFrame([0.15 for x in range(len(vdf_freq_List_service))],columns=['VDF_alpha{}'.format(num+1)]))
        List.append(pd.DataFrame([4 for x in range(len(vdf_freq_List_service))],columns=['VDF_beta{}'.format(num+1)]))
        List.append(pd.DataFrame(vdf_freq_List_service,columns=['VDF_freq{}'.format(num+1)]))
    
    vdf_service = pd.DataFrame()
    vdf_service = pd.concat(List,axis=1)
    
    service_link_vdf_csv = pd.concat([service_link_csv,vdf_service],axis=1)
    service_link_vdf_csv = service_link_vdf_csv.drop_duplicates(subset=['name']) ###
    service_link_vdf_csv = service_link_vdf_csv.sort_values(by=['name'])

    service_link_vdf_csv.insert(3, 'facility_type', '')
    service_link_vdf_csv.insert(4, 'dir_flag', 1)
    service_link_vdf_csv.insert(6, 'link_type', 3)
    service_link_vdf_csv.insert(7, 'link_type_name', 'r2r')
    # physical_link_csv.insert(7, 'VDF_fftt1', 0)
    service_link_vdf_csv.insert(9, 'lanes', 1)
    service_link_vdf_csv.insert(10, 'capacity', 5000)
    service_link_vdf_csv.insert(11, 'free_speed', 2)
    service_link_vdf_csv.insert(12, 'cost', 0)
    # transfer_link_vdf_csv.insert(14, 'VDF_cap1', 5000)
    # transfer_link_vdf_csv.insert(15, 'VDF_alpha1', 0.15)
    # transfer_link_vdf_csv.insert(16, 'VDF_beta1', 4)
    service_link_vdf_csv.insert(17, 'VDF_theta1', 1)
    service_link_vdf_csv.insert(18, 'VDF_gamma1', 1)
    service_link_vdf_csv.insert(19, 'VDF_mu1', 100)
    service_link_vdf_csv.insert(20, 'RUC_rho1', 10)
    service_link_vdf_csv.insert(21, 'RUC_resource1', 0)
    service_link_vdf_csv.insert(22, 'RUC_type', 1)

    # List.append(pd.DataFrame(active_distance / 5, columns=['VDF_fftt{}'.format(num + 1)]))

    service_link_vdf_csv_order = ['name','from_node_id','to_node_id','facility_type','dir_flag','directed_route_id','link_type','link_type_name','length','lanes','capacity','free_speed','cost','VDF_fftt1','VDF_cap1','VDF_alpha1','VDF_beta1','VDF_theta1','VDF_gamma1','VDF_mu1','RUC_rho1','RUC_resource1','RUC_type','VDF_freq1','geometry','mode_type','allowed_use']
    service_link_vdf_csv = service_link_vdf_csv[service_link_vdf_csv_order]
    
    #2.3 merge link
    Link_df = pd.concat([physical_link_csv,transfer_link_vdf_csv,service_link_vdf_csv])
    Link_df['agency_name'] = agency_name
    Link_df.index = pd.RangeIndex(len(Link_df.index))
    Link_df.index.name = 'link_id'
    Link_df.index += 1


    # Oct/31/2021 Get mode type for nodes
    Node_df_get_mode = copy.deepcopy(Node_df)
    Node_df_get_mode = Node_df_get_mode.reset_index()
    def get_node_mode(Node_df_row):
        if Node_df_row['node_id'] in Link_df['from_node_id'].unique():
             mode_type = Link_df[Link_df['from_node_id']==Node_df_row['node_id']].iloc[0]['mode_type']
        elif Node_df_row['node_id'] in Link_df['to_node_id'].unique():
             mode_type = Link_df[Link_df['to_node_id'] == Node_df_row['node_id']].iloc[0]['mode_type']
        else:
            mode_type = None
            print('Node not found in link list '+str(Node_df_row['node_id']))
        return mode_type
    Node_df_get_mode['mode_type'] = Node_df_get_mode.apply(get_node_mode, axis=1)
    Node_df_get_mode = Node_df_get_mode.set_index(['node_id'])
    Node_df['mode_type'] = Node_df_get_mode['mode_type']


    # Save to CSV

    Node_df.to_csv('transit_agency_{}_node.csv'.format(NUM))

    if NUM == 1:
        Node_df.to_csv('combined_node.csv', sep=",")
    else:
        Node_df.to_csv('combined_node.csv', mode='a+', header=False, sep=",")

    Link_df.to_csv('transit_agency_{}_link.csv'.format(NUM))

    if NUM == 1:
        Link_df.to_csv('combined_link.csv', sep=",")

    else:
        Link_df.to_csv('combined_link.csv', mode='a+', header=False, sep=",")

# Reset link_id
    if NUM == num_of_agency:
        Link_df = pd.read_csv('combined_link.csv')
        Link_df = Link_df.drop(['link_id'], axis=1)
        Link_df.index.name = 'link_id'
        Link_df.to_csv('combined_link.csv', sep=",")



    # print('Link: run time -->',time.time()-start_time)
    
    
    
    # '''4. TRIP'''
    # # start_time = time.time()
    # route_name_series = pd.Series(m_PT_RouteMap['route_long_name'].tolist(), index=m_PT_RouteMap['route_id'].tolist())
    # directed_route_id_series = pd.Series(m_PT_TripMap['directed_route_id'].tolist(), index=m_PT_TripMap['trip_id'].tolist())
    
    # trip_csv = pd.DataFrame()
    # length_temp = np.array(service_link_vdf_csv['length'])
    # from_node_temp = np.array(service_link_vdf_csv['from_node_id'])
    # to_node_temp = np.array(service_link_vdf_csv['to_node_id'])
    
    # trip_csv_list = []
    # for key in dataList_trip.keys():
    #     active_length_list = []
    #     active_node_sequence_size = len(dataList_trip[key]['route_stop_id_sequence'])
    #     flag = 1
    
    #     for i in range(active_node_sequence_size-1):
    #         active_from_node_id = dataList_trip[key]['node_id_sequence'][i]
    #         active_to_node_id = dataList_trip[key]['node_id_sequence'][i+1]
    #         temp1 = np.array(from_node_temp == active_from_node_id)
    #         temp2 = np.array(to_node_temp == active_to_node_id)
    #         temp = temp1 & temp2
    #         if not any(temp):
    #             flag = 0
    #             break
    
    #         active_length = length_temp[temp]
    #         active_length = active_length[0]
    #         active_length_list.append(active_length)
    
    #     if flag == 1:
    #         active_length = sum(active_length_list)
    #         active_time_sequence = dataList_trip[key]['time_sequence']
    #         if '' in active_time_sequence:
    #             active_time_sequence.remove('')
    
    #         active_time_first_temp = dataList_trip[key]['arrival_time_min_sequence'][0]
    #         active_time_last_temp = dataList_trip[key]['arrival_time_min_sequence'][-1]
    
    #         active_time = active_time_last_temp - active_time_first_temp
    #         if active_time < 0:
    #             active_time = active_time+1440
    
    #         node_sequence_temp = ';'.join(list(map(str, dataList_trip[key]['node_id_sequence'])))+';'
    #         time_sequence_temp = ';'.join(active_time_sequence)+';'
    
    #         active_arrival_time = dataList_trip[key]['arrival_time_min_sequence'][0]
    
    #         trip_csv_list.append([key,route_name_series[dataList_trip[key]['route_id']],
    #                               directed_route_id_series[key],
    #                               active_arrival_time,active_time,active_length,
    #                               node_sequence_temp,time_sequence_temp])
    
    
    # trip_csv = pd.DataFrame(trip_csv_list, columns=['trip_id','route_id_short_name','directed_route_id','arrival_time','travel_time','distance','node_sequence','time_sequence'])
    # trip_csv.insert(0, 'agent_type', 'transit')
    # trip_csv.insert(4, 'o_zone_id', '1')
    # trip_csv.insert(5, 'd_zone_id', '2')
    # trip_csv.insert(6, 'agency_name', agency_name)
    
    # def trip_geometry(x): # Input: node list
    #     x = x.split(';')
    
    #     geometry = ''
    #     for i in x[:-1]:
    #         active_from_route_stop_id_x = route_stop_x_series[int(i)]
    #         active_from_route_stop_id_y = route_stop_y_series[int(i)]
    #         geometry += str(active_from_route_stop_id_x)+' '+str(active_from_route_stop_id_y)+','
    #     geometry = 'LINESTRING (' + geometry[:-1] + ')'
    #     return geometry
    
    # trip_csv['geometry'] = trip_csv['node_sequence'].apply(lambda x: trip_geometry(x)) # 这句话有点慢
    # # trip_csv.to_csv('trip2.csv')
    
    # # print('Trip: run time -->',time.time()-start_time)
    
    
    # '''5. ROUTE'''
    # # route_csv = trip_csv.drop(['trip_id'],axis=1)
    # # route_csv['directed_route_id'] = route_csv['directed_route_id'].copy().apply(lambda x: x.split('.')[0])
    # # route_csv = route_csv.drop_duplicates(subset=['directed_route_id'])
    
    # # route_csv.index = pd.RangeIndex(len(route_csv.index))
    # # route_csv.index.name = 'route_id'
    # # route_csv.index += 1
    # # route_csv.to_csv('route2.csv')
    # # print('Route: run time -->',time.time()-start_time)
    
    
    # '''6. SERVICE'''
    # service_csv = trip_csv.drop(['trip_id'],axis=1)
    
    # def define_time_period(x):
    #     for ids in time_period_id:
    #         ids = ids-1
    #         if x>=from_time_min[ids] and x<to_time_min[ids]:
    #             return int(ids)+1
    # service_csv['time_period_id'] = trip_csv['arrival_time'].apply(lambda x: define_time_period(x))
    # service_csv = service_csv.dropna()
    
    # service_csv_count_series = service_csv['time_period_id'].groupby(service_csv['directed_route_id']).count()
    # service_csv_count_series = service_csv_count_series.rename('frequency')
    # service_csv = service_csv.drop_duplicates(subset=['directed_route_id'])
    # service_csv = service_csv.set_index('directed_route_id')
    
    # service_csv_count = pd.concat([service_csv,service_csv_count_series],axis=1)
    # service_csv_count = service_csv_count.reset_index()
    # service_csv_count = service_csv_count.rename(columns={'index':'directed_route_id'})
    # # service_csv_count.to_csv('service5.csv',index=False)
    
    # # print('Service: run time -->',time.time()-start_time)
    # return node_csv,route_stop_csv,Link_df,service_csv_count


def converting(path,gmns_path):
    start_time = time.time()
    files= os.listdir(path) 
    s = []
    for file in files: 
        path_sub =  path + '/' + file
        if os.path.isdir(path_sub):
            s.append(path_sub)
            # files1 = os.listdir(path_sub)
    if len(s) == 0:
        s.append(path)

    # Physical_Node_List = []
    # Route_Stop_List = []
    # Link_List = []
    # Route_List = []
    # node_num = 1
        
    for i in range(len(s)):
        
        print('For Agency{}...'.format(i+1))
        print('Agent Name : ' + str(s[i]))
        gtfs_path = s[i]
        
        convert_gmns(gtfs_path, gmns_path, i+1, len(s))

    #     node_csv,route_stop_csv,Link_df,service_csv_count = convert_gmns(gtfs_path,gmns_path,i+1)
    #     node_num = len(node_csv) + 1
        
    #     Physical_Node_List.append(node_csv)
    #     Route_Stop_List.append(route_stop_csv)
    #     Link_List.append(Link_df)
    #     Route_List.append(service_csv_count)
     
    # Physical_Node = pd.concat(Physical_Node_List)
    # Physical_Node.index = pd.RangeIndex(len(Physical_Node.index))
    # Physical_Node.index.name = 'node_id'
    # Physical_Node.index += 1
    
    # Route_Stop = pd.concat(Route_Stop_List)
    # NODE = pd.concat([Physical_Node,Route_Stop])
    # NODE_order = ['name','x_coord','y_coord','node_type','directed_route_id','ctrl_type','zone_id','production','attraction','agency_name','geometry']
    # NODE = NODE[NODE_order]
    # NODE.to_csv(gmns_path + os.sep + 'combined_node.csv')
    
    # LINK = pd.concat(Link_List)
    # LINK.index = pd.RangeIndex(len(LINK.index))
    # LINK.index.name = 'link_id'
    # LINK.index += 1
    # LINK.to_csv(gmns_path + os.sep + 'combined_link.csv')
    


    # ROUTE = pd.concat(Route_List)
    # ROUTE.index = pd.RangeIndex(len(ROUTE.index))
    # ROUTE.index.name = 'route_id'
    # ROUTE.index += 1
    # ROUTE.to_csv(gmns_path + os.sep + 'service.csv')
    print('run time -->',time.time()-start_time)



if __name__=='__main__':
    path = 'GTFS_DC'
    gmns_path = '.'
    converting(path,gmns_path)
    
