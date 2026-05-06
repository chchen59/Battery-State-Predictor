import datetime
import pandas as pd
from scipy.io import loadmat
from pandas import DataFrame

mat_files = ['B0005', 'B0006', 'B0007'] #list of .mat files to be converted to csv files

#define a function for extracting discharge and charge data
def disch_data(battery):
    mat = loadmat('data/' + battery + '.mat') #get the .mat file
    print('Total data in dataset: ', len(mat[battery][0, 0]['cycle'][0])) #get the length of the data from number of cycles
    c = 0 #set a variable to zero
    disdataset = [] #create an empty list for discharge data
    capacity_data = []
  
    for i in range(len(mat[battery][0, 0]['cycle'][0])):
        row = mat[battery][0, 0]['cycle'][0, i] #get each row of the cycle
        if row['type'][0] == 'discharge': #if the row is a dicharge cycle
            ambient_temperature = row['ambient_temperature'][0][0] #get temp,date_time stamp,capacity,voltage,current etc,.
            date_time = datetime.datetime(int(row['time'][0][0]),
                                int(row['time'][0][1]),
                                int(row['time'][0][2]),
                                int(row['time'][0][3]),
                                int(row['time'][0][4])) + datetime.timedelta(seconds=int(row['time'][0][5]))
            data = row['data']
            capacity = data[0][0]['Capacity'][0][0]
            type = 'discharge'
            test_name = battery
            for j in range(len(data[0][0]['Voltage_measured'][0])):
                voltage_measured = data[0][0]['Voltage_measured'][0][j]
                current_measured = data[0][0]['Current_measured'][0][j]
                temperature_measured = data[0][0]['Temperature_measured'][0][j]
                current_load = data[0][0]['Current_load'][0][j]
                voltage_load = data[0][0]['Voltage_load'][0][j]
                time = data[0][0]['Time'][0][j]
                disdataset.append([test_name, c + 1, type, ambient_temperature, date_time, capacity,
                        voltage_measured, current_measured,
                        temperature_measured, current_load,
                        voltage_load, time])
                capacity_data.append([test_name, c + 1, ambient_temperature, date_time, capacity])
            c = c + 1
    print(disdataset[0])
    return [pd.DataFrame(data=disdataset,
            columns=['test_name', 'cycle', 'type', 'ambient_temperature', 'datetime',
                'capacity', 'voltage_measured',
                'current_measured', 'temperature_measured',
                'current', 'voltage', 'time']),
        pd.DataFrame(data=capacity_data,
            columns=['test_name', 'cycle', 'ambient_temperature', 'datetime',
                'capacity'])]

def charge_data(battery): #similarly write a fn for charge data
    mat = loadmat('data/' + battery + '.mat')
    c = 0
    chdataset = []

    for i in range(len(mat[battery][0, 0]['cycle'][0])):
        row = mat[battery][0, 0]['cycle'][0, i]
        if row['type'][0] == 'charge' :
    
            ambient_temperature = row['ambient_temperature'][0][0]
            date_time = datetime.datetime(int(row['time'][0][0]),
                        int(row['time'][0][1]),
                        int(row['time'][0][2]),
                        int(row['time'][0][3]),
                        int(row['time'][0][4])) + datetime.timedelta(seconds=int(row['time'][0][5]))
            data = row['data']
            type = 'charge'
            test_name = battery
            for j in range(len(data[0][0]['Voltage_measured'][0])):
                voltage_measured = data[0][0]['Voltage_measured'][0][j]
                current_measured = data[0][0]['Current_measured'][0][j]
                temperature_measured = data[0][0]['Temperature_measured'][0][j]
                current_charge = data[0][0]['Current_charge'][0][j]
                voltage_charge = data[0][0]['Voltage_charge'][0][j]
                time = data[0][0]['Time'][0][j]
                chdataset.append([test_name, c + 1, type, ambient_temperature, date_time,
                    voltage_measured, current_measured,
                    temperature_measured, current_charge,
                    voltage_charge, time])
            c = c + 1
    print(chdataset[788])
    chdf=pd.DataFrame(data=chdataset,columns=['test_name', 'cycle', 'type', 'ambient_temperature', 'datetime', 
                'voltage_measured','current_measured',
                'temperature_measured','current',
                'voltage', 'time']) 
    return chdf

for battery in mat_files:
    disch_df, cap_df = disch_data(battery)
    ch_df = charge_data(battery)
    pd.set_option('display.max_columns', 12)
    print(ch_df)
    print(disch_df)
    whole_df = pd.concat([ch_df, disch_df], ignore_index=True)
    whole_df=whole_df.sort_values(by=['cycle', 'type'], ascending=[True, True])
    disch_df.to_csv('csv_data/' + 'discharge_' + battery + '.csv', index=False)
    ch_df.to_csv('csv_data/' + 'charge_' + battery + '.csv', index=False)
    whole_df.to_csv('csv_data/' + battery + '.csv', index=False)
