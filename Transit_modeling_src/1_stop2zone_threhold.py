# -*- coding: utf-8 -*-
import os
import math
import heapq
import numpy as np
import pandas as pd

# WGS84 transfer coordinate system to distance: meter
def LLs2Dist(lon1, lat1, lon2, lat2):
    R = 6371
    dLat = (lat2 - lat1) * math.pi / 180.0
    dLon = (lon2 - lon1) * math.pi / 180.0
    a = math.sin(dLat / 2) * math.sin(dLat/2) + math.cos(lat1 * math.pi / 180.0) * math.cos(lat2 * math.pi / 180.0) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist = R * c * 1000 / 1609 # 1mile = 1609 meter
    return dist


def createConnector(dataList, from_node_id, to_node_id):
    link = []
    from_node_id_x = dataList[from_node_id]['x_coord']
    from_node_id_y = dataList[from_node_id]['y_coord']
    from_node_mode_type = dataList[from_node_id]['mode_type']
    to_node_id_x = dataList[to_node_id]['x_coord']
    to_node_id_y = dataList[to_node_id]['y_coord']
    to_node_mode_type = dataList[to_node_id]['mode_type']

    length = LLs2Dist(from_node_id_x,from_node_id_y,to_node_id_x,to_node_id_y)
    # VDF_fftt = length / 2 * 60  # min
    geometry = 'LINESTRING (' + str(from_node_id_x)+' '+str(from_node_id_y)+', '+str(to_node_id_x)+' '+str(to_node_id_y)+')'

    if length < 1:
        if from_node_mode_type == '':
            link_mode_type = 'walk' + '2' + to_node_mode_type
        else:
            link_mode_type = 'walk' + '2' + from_node_mode_type
    else:
        if from_node_mode_type == '':
            link_mode_type = 'drive' + '2' + to_node_mode_type
        else:
            link_mode_type = 'drive' + '2' + from_node_mode_type

    allowed_use = ''
    if link_mode_type == 'walk2bus':
        allowed_use = 'w_bus;w_bus_metro'
    elif link_mode_type == 'walk2metro':
        allowed_use = 'w_metro;w_bus_metro'
    elif link_mode_type == 'drive2bus':
        allowed_use = 'd_bus;d_bus_metro'
    elif link_mode_type == 'drive2metro':
        allowed_use = 'd_metro;d_bus_metro'

    link = [from_node_id, to_node_id, length, geometry, link_mode_type, allowed_use]
    return link

# def link_mode_type(Connector_row):
#     if Connector_row['length'] < 1:
#         link_mode = 'walk'
#     else:
#         link_mode = 'drive'
#     return link_mode

def VDF_FFTT(Connector_row):
    if Connector_row['length'] < 0.5:
        VDF_fftt = Connector_row['length'] / 2 * 60  # min
    elif (Connector_row['length'] >= 0.5) & (Connector_row['length'] < 1):
        VDF_fftt = Connector_row['length'] / 2 * 60 + 5  # min
    else:
        VDF_fftt = Connector_row['length'] / 40 * 60  # min
    return VDF_fftt

def generate_walking_line(file1,file2):

    node_transit1 = pd.read_csv(zone_path + os.sep + 'node.csv', encoding='gbk',low_memory=False) # zone
    node_transit1 = node_transit1[node_transit1['zone_id'] > 1] # find zone
    node_transit1 = node_transit1.reset_index(drop=True)
    # node_transit1 = node_transit1[node_transit1['node_type']=='stop'] # only physical node
    
    node_transit2 = pd.read_csv(file2, low_memory=False) # transit node
    node_transit2 = node_transit2[node_transit2['node_type'] == 'stop'] # only physical node

    node_combine = pd.DataFrame()
    node_combine['node_id']= node_transit2['node_id'].tolist() + node_transit1['node_id'].tolist()
    node_combine['x_coord']= node_transit2['x_coord'].tolist() + node_transit1['x_coord'].tolist()
    node_combine['y_coord'] = node_transit2['y_coord'].tolist() + node_transit1['y_coord'].tolist()
    node_combine['zone_id']= node_transit2['zone_id'].tolist() + node_transit1['zone_id'].tolist()

    # Get mode type of node
    agency_link = pd.read_csv
    dict_mode_type = pd.DataFrame()

    def get_terminal_flag(node_id):
        return node_transit2[node_transit2['node_id']==node_id].iloc[0]['terminal_flag']

    def get_mode_type(node_id):
        if node_id in node_transit2['node_id'].unique():
            node_type = node_transit2[node_transit2['node_id']==node_id].iloc[0]['mode_type']
        else:
            node_type = ''
        return node_type

    
    dataList_stop1 = {} # zone list
    gp = node_transit1.groupby('node_id')
    for key, form in gp:
        dataList_stop1[key] = {  # zones
            'x_coord': form['x_coord'].values[0],
            'y_coord': form['y_coord'].values[0],
            }
    
    dataList_stop2 = {} # node list
    gp = node_transit2.groupby('node_id')
    for key, form in gp:
        dataList_stop2[key] = {
            'x_coord': form['x_coord'].values[0],
            'y_coord': form['y_coord'].values[0],
            'terminal_flag': get_terminal_flag(key),
            'mode_type': get_mode_type(key)
            }
    
    dataList = {}
    gp = node_combine.groupby('node_id')
    for key, form in gp:
        dataList[key] = {
            'x_coord': form['x_coord'].values[0],
            'y_coord': form['y_coord'].values[0],
            'mode_type': get_mode_type(key)
            }
    
    
    coord_list = []
    for key in dataList_stop2.keys(): 
        coord_list.append((dataList_stop2[key]['x_coord'], dataList_stop2[key]['y_coord']))
    coord_array = np.array(coord_list)
    





    # print('building connector...')
    link_list = []
    zone_count = 0
    zone_connector_csv = pd.DataFrame()
    for key in dataList_stop1.keys():  # Numerate on Zones
        coord = np.array((dataList_stop1[key]['x_coord'], dataList_stop1[key]['y_coord']))
      
        List = []

        # Oct/31/2021
        for key_ in dataList_stop2.keys():
            length = LLs2Dist(coord[0], coord[1], dataList_stop2[key_]['x_coord'], dataList_stop2[key_]['y_coord'])
            if dataList_stop2[key_]['terminal_flag'] == True:
                if (dataList_stop2[key_]['mode_type'] == 'rail')|(dataList_stop2[key_]['mode_type'] == 'metro'):
                    length = max(0.1, length - 12)
                else:
                    length = max(0.1, length - 2)

            List.append(length)

        # for i in range(len(coord_array)):
        #     length = LLs2Dist(coord[0],coord[1],coord_array[i][0],coord_array[i][1])
        #     List.append(length)

        distance = np.array(List) 
        count = 1
        # while (count):
        idx_temp = heapq.nsmallest(count, distance.tolist())
        idx = np.where(distance == idx_temp[count-1])

        if distance[idx][0] > 1:
            continue
            print(distance[idx],key)

        # for drive
        distance_true_15 = distance

        # for walk and drive < 3
        distance_true = np.logical_and(distance>0, distance<=3)
        arr = np.arange(len(distance_true))
        index_true = arr[distance_true]

        if len(index_true) > 0:
            zone_count += 1
            zone_connector_csv = zone_connector_csv.append(node_transit1[node_transit1['zone_id'] == key])


        
        for j in range(len(index_true)):
            
            active_node = node_transit2['node_id'].iloc[index_true[j]]
            # if ((active_node[idx[0][0]] in link_road['from_node_id'].tolist()) and (active_node[idx[0][0]] in link_road['to_node_id'].tolist())):
            active_link1 = createConnector(dataList, active_node, key)
            active_link2= createConnector(dataList, key, active_node)
            link_list.append(active_link1)
            link_list.append(active_link2)

    connector_csv = pd.DataFrame()
    connector_csv = pd.DataFrame(link_list, columns=['from_node_id','to_node_id','length','geometry', 'mode_type', 'allowed_use']).drop_duplicates()


    agency_name = node_transit2['agency_name'][0]
    zone_connector_csv['agency_name'] = agency_name


    # print in console

    print(agency_name.center(36)+'|'+str(zone_count).center(16))


    return connector_csv, zone_connector_csv
    

if __name__=='__main__':
    
    gmns_path = '.'
    zone_path = '.' # node_id
    files = os.listdir(gmns_path)
    
    s = []
    k = 1
    while k < len(files):
        if 'transit_agency_{}_node.csv'.format(k) in files:
            s.append('transit_agency_{}_node.csv'.format(k))
        k += 1
    
    Connector_List = []
    Zone_Connector_List = []
    total_zones = 0

    # Nov 11 print table in console
    print('Agency Name'.center(36) + '| Covered Zones ')
    print('————————————————————————————————————————————————————————')
    for file in s:
        connector_csv, zone_connector_csv = generate_walking_line(zone_path, file)
        Connector_List.append(connector_csv)
        Zone_Connector_List.append(zone_connector_csv)








    
    # gmns_path = '.'
    # files= os.listdir(gmns_path) 
    
    # s = []
    # k = 1
    # while k < len(files):
    #     if 'transit_agency_{}_node.csv'.format(k) in files:
    #         s.append('transit_agency_{}_node.csv'.format(k))
    #     k += 1
    
    # Connector_List = []

    # connector_csv = generate_walking_line(s[1],s[1])
    Connector_List.append(connector_csv)
    
    Connector = pd.concat(Connector_List)
    Connector['name'] = None
    Connector['facility_type'] = ''
    Connector['dir_flag'] = 1
    Connector['directed_route_id'] = ''
    Connector['link_type'] = 5
    Connector['link_type_name'] = 'z2sta'
    Connector['lanes'] = 1
    Connector['capacity'] = 5000
    Connector['free_speed'] = 2
    Connector['cost'] = 0
    Connector['VDF_cap1'] = 5000
    Connector['VDF_alpha1'] = 0.15
    Connector['VDF_beta1'] = 4
    Connector['VDF_theta1'] = 1
    Connector['VDF_gamma1'] = 1
    Connector['VDF_mu1'] = 100
    Connector['RUC_rho1'] = 10
    Connector['RUC_resource1'] = 0
    Connector['RUC_type'] = 1
    Connector['VDF_freq1'] = 24

    # Connector['mode_type'] = Connector.apply(link_mode_type, axis=1)
    Connector['VDF_fftt1'] = Connector.apply(VDF_FFTT, axis=1)

    Connector.index.name = 'link_id'
    Connector.index += 1
    
    Connector_order = ['name', 'from_node_id', 'to_node_id', 'facility_type', 'dir_flag', 'directed_route_id', 'link_type', 'link_type_name', 'length', 'lanes', 'capacity', 'free_speed', 'cost', 'VDF_fftt1', 'VDF_cap1', 'VDF_alpha1', 'VDF_beta1', 'VDF_theta1', 'VDF_gamma1', 'VDF_mu1', 'RUC_rho1', 'RUC_resource1', 'RUC_type', 'VDF_freq1', 'geometry', 'mode_type', 'allowed_use']
    Connector = Connector[Connector_order]
    covered_zones = len(Connector[Connector.index % 2 == 0]['from_node_id'].unique())
    print('————————————————————————————————————————————————————————')
    print(f'Total {len(s)} Agencies'.center(36) + '|' + str(covered_zones).center(16))
    print('\nSaving to csv file...')

    Zone_Connector = pd.concat(Zone_Connector_List)

    Connector.to_csv('zone2stop_link.csv')
    Zone_Connector.to_csv('zone_agency.csv')


