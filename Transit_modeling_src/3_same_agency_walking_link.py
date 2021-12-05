# -*- coding: utf-8 -*-
import os
import math
import heapq
import numpy as np
import pandas as pd

# WGS84 transfer coordinate system to distance: mile
def LLs2Dist(lon1, lat1, lon2, lat2):
    R = 6371
    dLat = (lat2 - lat1) * math.pi / 180.0
    dLon = (lon2 - lon1) * math.pi / 180.0
    a = math.sin(dLat / 2) * math.sin(dLat/2) + math.cos(lat1 * math.pi / 180.0) * math.cos(lat2 * math.pi / 180.0) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist = R * c * 1000 / 1609  # 1mile = 1609 meter
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
    VDF_fftt = length / 2 * 60  # min
    geometry = 'LINESTRING (' + str(from_node_id_x)+' '+str(from_node_id_y)+', '+str(to_node_id_x)+' '+str(to_node_id_y)+')'
    link_mode_type = str(from_node_mode_type) + '2' + str(to_node_mode_type)

    allowed_use = ''
    if link_mode_type == 'bus2bus':
        allowed_use = 'w_bus;w_bus_metro;d_bus;d_bus_metro'
    elif link_mode_type == 'metro2metro':
        allowed_use = 'w_metro;w_bus_metro;d_metro;d_bus_metro'
    elif (link_mode_type == 'bus2metro') | (link_mode_type == 'metro2bus'):
        allowed_use = 'w_bus_metro;d_bus_metro'

    link = [from_node_id, to_node_id, length, geometry, VDF_fftt, link_mode_type, allowed_use]
    return link


def generate_walking_line(file1,file2):

    node_transit1 = pd.read_csv(file1 ,low_memory=False) # transit node
    node_transit1 = node_transit1[node_transit1['node_type']=='stop'] # only physical node
    
    node_transit2 = pd.read_csv(file2 ,low_memory=False) # transit node
    node_transit2 = node_transit2[node_transit2['node_type']=='stop'] # only physical node

    node_combine = pd.DataFrame()
    node_combine['node_id']= node_transit2['node_id'].tolist() + node_transit1['node_id'].tolist()
    node_combine['x_coord']= node_transit2['x_coord'].tolist() + node_transit1['x_coord'].tolist()
    node_combine['y_coord'] = node_transit2['y_coord'].tolist() + node_transit1['y_coord'].tolist()
    node_combine['zone_id']= node_transit2['zone_id'].tolist() + node_transit1['zone_id'].tolist()
    
    def get_mode_type(node_id):
        return node_transit2[node_transit2['node_id']==node_id].iloc[0]['mode_type']

    dataList_stop1 = {} # transit node agency1
    gp = node_transit1.groupby('node_id')
    for key, form in gp:
        dataList_stop1[key] = {
            'x_coord': form['x_coord'].values[0],
            'y_coord': form['y_coord'].values[0]
            }
    
    dataList_stop2 = {} # transit node agency1
    gp = node_transit2.groupby('node_id')
    for key, form in gp:
        dataList_stop2[key] = {
            'x_coord': form['x_coord'].values[0],
            'y_coord': form['y_coord'].values[0],
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
        coord_list.append((dataList_stop2[key]['x_coord'],dataList_stop2[key]['y_coord']))
    coord_array = np.array(coord_list)
    
    
    # print('building connector...')
    link_list = []
    
    for key in dataList_stop1.keys(): 
        coord = np.array((dataList_stop1[key]['x_coord'],dataList_stop1[key]['y_coord']))
      
        List = []
        for i in range(len(coord_array)):
            length = LLs2Dist(coord[0],coord[1],coord_array[i][0],coord_array[i][1])
            List.append(length)
        distance = np.array(List) 
        count = 1
        # while (count):
        idx_temp = heapq.nsmallest(count, distance.tolist())
        idx = np.where(distance == idx_temp[count-1])
        if distance[idx][0] > 1:
            continue
            print(distance[idx],key)
        
        distance_true = np.logical_and(distance>0, distance<=0.5)
        arr = np.arange(len(distance_true))
        index_true = arr[distance_true]
        
        for j in range(len(index_true)):
            
            active_node = node_transit2['node_id'].iloc[index_true[j]]
            # if ((active_node[idx[0][0]] in link_road['from_node_id'].tolist()) and (active_node[idx[0][0]] in link_road['to_node_id'].tolist())):
            active_link1 = createConnector(dataList, active_node, key)
            active_link2= createConnector(dataList, key, active_node)
            link_list.append(active_link1)
            link_list.append(active_link2)
    

    connector_csv = pd.DataFrame()
    connector_csv = pd.DataFrame(link_list, columns=['from_node_id','to_node_id','length','geometry','VDF_fftt1','mode_type','allowed_use']).drop_duplicates()
    
    return connector_csv
    

def combine_link_csv():
    transit_link = pd.read_csv('./combined_link.csv')
    same_agency_link = pd.read_csv('./walking_link_transit_same_agency.csv')
    # different_agency_link = pd.read_csv('./walking_link_transit_different_agency.csv')
    zone2sta_link = pd.read_csv('./zone2stop_link.csv')
    total_link = pd.concat([transit_link, same_agency_link, zone2sta_link])
    total_link.reset_index()
    total_link = total_link.fillna('')
    total_link = total_link.rename(columns={'link_id': 'original_link_id'})
    total_link.index.name = 'link_id'
    total_link.to_csv('./total_link.csv')

# def combine_node_csv():
#     transit_node = pd.read_csv('./combined_node.csv')
#     zone_agency = pd.read_csv('./zone_agency.csv')
#     zone_node = zone_agency.drop('agency_name')
#     zone_node = zone_node.drop_duplicates()
#     total_node = pd.concat([transit_node, zone_node])
#     total_node = total_node.fillna('')
#     total_node.to_csv('./total_node.csv', index=False)



if __name__=='__main__':
        
    gmns_path = '.'
    files= os.listdir(gmns_path) 
    
    s = []
    k = 1
    while k < len(files):
        if 'transit_agency_{}_node.csv'.format(k) in files:
            s.append('transit_agency_{}_node.csv'.format(k))
        k += 1
    
    Connector_List = []

    for i in s:
        connector_csv = generate_walking_line(i,i)
        Connector_List.append(connector_csv)
    
    Connector = pd.concat(Connector_List)
    Connector['name'] = None
    Connector['facility_type'] = ''
    Connector['dir_flag'] = 1
    Connector['directed_route_id'] = ''
    Connector['link_type'] = 4
    Connector['link_type_name'] = 'sta2sta_2r'
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

    Connector.index.name = 'link_id'
    Connector.index += 1
    
    Connector_order = ['name', 'from_node_id', 'to_node_id', 'facility_type', 'dir_flag', 'directed_route_id',
                       'link_type', 'link_type_name', 'length', 'lanes', 'capacity', 'free_speed', 'cost', 'VDF_fftt1',
                       'VDF_cap1', 'VDF_alpha1', 'VDF_beta1', 'VDF_theta1', 'VDF_gamma1', 'VDF_mu1', 'RUC_rho1',
                       'RUC_resource1', 'RUC_type', 'VDF_freq1', 'geometry', 'mode_type', 'allowed_use']
    Connector = Connector[Connector_order]
    Connector.to_csv('walking_link_transit_same_agency.csv')