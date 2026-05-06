import logging
from pathlib import Path

import numpy as np
import pandas as pd


class ChargeCycleCols:
    TEST_NAME = 0
    CYCLE_INDEX = 1
    TYPE = 2
    AMBIENT_TEMPERATURE = 3
    DATE_TIME = 4
    VOLTAGE_MEASURED = 5
    CURRENT_MEASURED = 6
    TEMPERATURE_MEASURED = 7
    CURRENT_CHARGE = 8
    VOLTAGE_CHARGE = 9
    TIME = 10
    CAPACITY = 11
    SOH = 12

class DischargeCycleCols:
    TEST_NAME = 0
    CYCLE_INDEX = 1
    TYPE = 2
    AMBIENT_TEMPERATURE = 3
    DATE_TIME = 4
    VOLTAGE_MEASURED = 5
    CURRENT_MEASURED = 6
    TEMPERATURE_MEASURED = 7
    CURRENT_DISCHARGE = 8
    VOLTAGE_DISCHARGE = 9
    TIME = 10
    CAPACITY = 11
    SOH = 12
    SOC = 13

class NASAData():
    def __init__(self,
                chunk_size=1000000,
                data_files=['B0005', 'B0006'],
                base_path="./"):

        self.logger = logging.getLogger()
        self.chunksize = chunk_size
        self.base_path = base_path
        self.data_files = data_files

        self.__load_raw_data()

    def __load_raw_data(self):
        self.__load_csv_to_raw()
        self.__clean_cycle_raw()
        self.__assign_charge_raw()
        self.__assign_discharge_raw()
        self.__filter_unmatch_raw()

    def __load_csv_to_raw(self):

        self.cycle_raw=pd.DataFrame()

        for data_file in self.data_files:
            file_path = Path(self.base_path) / f"{data_file}.csv"

            if not file_path.is_file():
                self.logger.error(f"Data file {file_path} does not exist.")
                continue

            iter_cycele_raw = pd.read_csv(file_path, chunksize=self.chunksize)
            for cycle in iter_cycele_raw:
                self.cycle_raw = pd.concat([self.cycle_raw, cycle], ignore_index=True)
    
        self.logger.debug("Finish loading data.")
        self.logger.info("Loaded raw NASA data with cycle row count: %s " %
                         (len(self.cycle_raw)))

    def __clean_cycle_raw(self):
        self.logger.debug("Start cleaning cycle raw data...")
        count_before = len(self.cycle_raw)

        # Voltage outside 0.1 ~ 5.0 are seen as abnormal dataset
        self.cycle_raw = self.cycle_raw.drop(
            self.cycle_raw[(self.cycle_raw['voltage_measured'] > 5.0)
                           | (self.cycle_raw['voltage_measured'] < 0.1)].index)

        self.logger.debug("Finish cleaning cycle raw data.")
        self.logger.info("Removed %s rows of abnormal cycle raw data." %
                         (count_before - len(self.cycle_raw)))

    def __filter_unmatch_raw(self):
        # 找出兩個表中共同的 [test_name, cycle] 組合
        # 我們先提取兩個表各自唯一的組合
        keys_charge = self.charge_cyc_raw[['test_name', 'cycle']].drop_duplicates()
        keys_discharge = self.discharge_cyc_raw[['test_name', 'cycle']].drop_duplicates()

        # 3. 使用 merge 取得兩個組合的交集 (Inner Join)
        common_keys = pd.merge(keys_charge, keys_discharge, on=['test_name', 'cycle'])

        # 4. 根據這個共同組合清單過濾原始資料
        # 使用 merge (inner join) 到原始資料上，即可只保留存在的組合
        self.charge_cyc_raw = pd.merge(self.charge_cyc_raw, common_keys, on=['test_name', 'cycle'])
        self.discharge_cyc_raw = pd.merge(self.discharge_cyc_raw, common_keys, on=['test_name', 'cycle'])

    def __assign_charge_raw(self):
        self.logger.debug("Start assigning charging raw data...")

        self.charge_cyc_raw = self.cycle_raw[self.cycle_raw['type']
                                                == 'charge']

        self.logger.debug("Finish assigning charging raw data.")
        self.logger.info("[Charging] cycle raw count: %s"
                         % (len(self.charge_cyc_raw)))

    def __assign_discharge_raw(self):
        self.logger.debug("Start assigning discharging raw data...")

        self.discharge_cyc_raw = self.cycle_raw[self.cycle_raw['type']
                                                == 'discharge']

        self.logger.debug("Finish assigning discharging raw data.")
        self.logger.info("[Discharging] cycle raw count: %s"
                         % (len(self.discharge_cyc_raw)))

    def prepare_data(self, train_names, test_names):
        self.logger.debug("Start preparing data for training: %s and testing: %s..."
                          % (train_names, test_names))

        self.train_charge_cyc = self.__get_cyc(
            train_names, self.charge_cyc_raw
        )

        self.test_charge_cyc = self.__get_cyc(
            test_names, self.charge_cyc_raw
        )
        self.logger.debug("Finish getting training and testing charge data.")

        self.train_discharge_cyc = self.__get_cyc(
            train_names, self.discharge_cyc_raw
        )

        self.test_discharge_cyc = self.__get_cyc(
            test_names, self.discharge_cyc_raw
        )
        self.logger.debug(
            "Finish getting training and testing discharge data.")

        self.train_discharge_cyc = self.__add_discharge_soh_pars(
            self.train_discharge_cyc, train_names
        )

        self.test_discharge_cyc = self.__add_discharge_soh_pars(
            self.test_discharge_cyc, test_names
        )

        self.logger.debug(
            "Finish adding training and testing discharge SOH parameters.")

        self.train_discharge_cyc = self.__add_discharge_soc_pars(
            self.train_discharge_cyc
        )

        self.test_discharge_cyc = self.__add_discharge_soc_pars(
            self.test_discharge_cyc
        )

        self.logger.debug(
            "Finish adding training and testing discharge SOC parameters.")

        self.train_charge_cyc = self.__add_charge_soh_pars(
            self.train_charge_cyc, self.train_discharge_cyc
        )

        self.test_charge_cyc = self.__add_charge_soh_pars(
            self.test_charge_cyc, self.test_discharge_cyc
        )

        self.logger.debug(
            "Finish adding training and testing charge SOH parameters.")

        self.logger.debug("Finish preparing data.")
        self.logger.info("Prepared training charge cycle data: %s" %
                         (self.train_charge_cyc.shape))
        self.logger.info("Prepared testing charge cycle data: %s" %
                         (self.test_charge_cyc.shape))
        self.logger.info("Prepared training discharge cycle data: %s" %
                         (self.train_discharge_cyc.shape))
        self.logger.info("Prepared testing discharge cycle data: %s" %
                         (self.test_discharge_cyc.shape))

    def __get_cyc(self, names, cyc_raw):
        cyc_data = []

        gp_cyc_raw = self.__group_cyc_by_name(cyc_raw, names)

        for test_name in names:
            for cycle in gp_cyc_raw[test_name]:
                cycle = cycle.reset_index(drop=True)
                cyc_data.append(cycle.values)

        # Modify by CHChen59
        cyc_data = np.array(cyc_data, dtype=object)
        return cyc_data

    def __group_cyc_by_name(self, cyc_raw, test_names):
        grouped_cycle = self.__group_cyc_by_name_and_cyc_count(cyc_raw)
        grouped_name_cycle = {}
        for key, group in grouped_cycle:
            test_name = key[0]
            if(test_name not in grouped_name_cycle):
                grouped_name_cycle[test_name] = []
            grouped_name_cycle[test_name].append(group)
        return grouped_name_cycle

    def __group_cyc_by_name_and_cyc_count(self, cyc_raw):
        return cyc_raw.groupby(
            ['test_name', (cyc_raw['cycle'] !=
                           cyc_raw['cycle'].shift()).cumsum()]
        )

    def __add_discharge_soc_pars(self, discharge_cyc):
        capacity_init = 0
        for c in range(len(discharge_cyc)):
            discharge_cyc[c] = np.c_[discharge_cyc[c],
                    np.zeros(discharge_cyc[c].shape[0])]
            for s in range(len(discharge_cyc[c])):
                sample = discharge_cyc[c][s] 
                time = sample[DischargeCycleCols.TIME]
                if time == 0:
                    capacity_init = sample[DischargeCycleCols.CAPACITY]
                    time_prev = 0
                    Qcumsum = 0 
                time_delta = time - time_prev
                time_prev = time
                current_abs = abs(sample[DischargeCycleCols.CURRENT_MEASURED])
                Q = (current_abs * time_delta) / 3600
                Qcumsum = Qcumsum + Q
                soc = ( 1- (Qcumsum  /capacity_init))  
                soc = max(0, min(1, soc))
                discharge_cyc[c][s][DischargeCycleCols.SOC] = soc
        return discharge_cyc

    def __add_discharge_soh_pars(self, discharge_cyc, names):
        for c in range(len(discharge_cyc)):
            discharge_cyc[c] = np.c_[discharge_cyc[c],
                                        np.zeros(discharge_cyc[c].shape[0])]
        for name in names:
            max_capacity = 0
            for cyc in discharge_cyc:
                if cyc[0][DischargeCycleCols.TEST_NAME] == name:
                    capacity = cyc[0][DischargeCycleCols.CAPACITY]
                    max_capacity = max(max_capacity, capacity)

            for cyc in discharge_cyc:
                if cyc[0][DischargeCycleCols.TEST_NAME] == name:
                    cyc[:, DischargeCycleCols.SOH] = (cyc[0][DischargeCycleCols.CAPACITY] / max_capacity)
        return discharge_cyc

    def __add_charge_soh_pars(self, charge_cyc, discharge_cyc):
        for c in range(len(charge_cyc)):
            charge_cyc[c] = np.c_[charge_cyc[c],
                                        np.zeros(charge_cyc[c].shape[0])]

        for c_cyc in charge_cyc:
            test_name = c_cyc[0][ChargeCycleCols.TEST_NAME]
            cycle_index = c_cyc[0][ChargeCycleCols.CYCLE_INDEX]

            for d_cyc in discharge_cyc:
                if d_cyc[0][DischargeCycleCols.TEST_NAME] == test_name and d_cyc[0][DischargeCycleCols.CYCLE_INDEX] == cycle_index:
                    c_cyc[:, ChargeCycleCols.SOH] = d_cyc[0][DischargeCycleCols.SOH]
        return charge_cyc

    def get_charge_data(self):
        return (
            self.train_charge_cyc,
            self.test_charge_cyc,
        )

    def get_discharge_data(self):
        return (
            self.train_discharge_cyc,
            self.test_discharge_cyc,
        )