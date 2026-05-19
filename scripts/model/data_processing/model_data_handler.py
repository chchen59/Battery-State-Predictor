import logging

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from .NASA_data import ChargeCycleCols, DischargeCycleCols

class ModelDataHandler():
    def __init__(self, dataset, x_cyc_indices, scaler_type=MinMaxScaler):
        self.logger = logging.getLogger()
        self.dataset = dataset
        self.x_cyc_indices = x_cyc_indices
        self.scaler_type = scaler_type

        self.train_charge_cyc, self.test_charge_cyc = self.dataset.get_charge_data()
        self.train_discharge_cyc, self.test_discharge_cyc = self.dataset.get_discharge_data()

        self.__assign_scalers()

    def __assign_scalers(self):
        self.charge_scalers = self.__create_scalers(self.train_charge_cyc)
        self.discharge_scalers = self.__create_scalers(
            self.train_discharge_cyc)

    def __create_scalers(self, cyc):
        scalers = []
        for index in self.x_cyc_indices:
            scalers.append(self.__create_cyc_scaler(cyc, index))
        return scalers

    def __create_cyc_scaler(self, cyc, col_index):
        data = np.concatenate(cyc)[:, col_index].reshape(-1, 1)
        scaler_x = self.scaler_type()
        scaler_x.fit_transform(data)
        return scaler_x

    def get_scalers(self):
        return self.charge_scalers, self.discharge_scalers

    def get_charge_whole_cycle(self, multiple_output=False, soh=True):
        """x: [ [[voltage, current, temperature], ...], ...] \n
        SOH y (single step): [ [soh], ... ] \n
        SOH y (multiple steps): [ [[soh], ...], ... ]\n
        """
        y_indices = [
            ChargeCycleCols.SOH,
        ]
        train_raw_x, train_y = self.__get_whole_cycle_soh_x_y(
            self.train_charge_cyc, self.x_cyc_indices, y_indices
        )
        test_raw_x, test_y = self.__get_whole_cycle_soh_x_y(
            self.test_charge_cyc, self.x_cyc_indices, y_indices
        )

        train_scaled_x = self.__get_scaled_whole_cycle_x(
            train_raw_x, self.charge_scalers)
        test_scaled_x = self.__get_scaled_whole_cycle_x(
            test_raw_x, self.charge_scalers)

        train_x, test_x = self.__get_padded_whole_cycle(
            train_scaled_x, test_scaled_x)

        train_raw_x, test_raw_x = self.__get_padded_whole_cycle(
            train_raw_x, test_raw_x)
        
        if(multiple_output):
            # (SOH only) duplicate the y values to multiple steps for each cycle
            train_y = np.repeat(train_y[:, None, :], train_x.shape[1], axis=1)
            test_y = np.repeat(test_y[:, None, :], test_x.shape[1], axis=1)

        self.logger.info("Train x: %s, train raw x: %s, train y: %s | Test x: %s, test raw x: %s, test y: %s" %
                         (train_x.shape, train_raw_x.shape, train_y.shape, test_x.shape, test_raw_x.shape, test_y.shape))

        return (train_x, train_raw_x, train_y, test_x, test_raw_x, test_y)


    def get_discharge_whole_cycle(self, output_capacity=False, multiple_output=False, soh=False):
        """x: [ [[voltage, current, temperature], ...], ...] \n
        SOH y (single step): [ [soh/last_charging_capacity], ... ] \n
        SOH y (multiple steps): [ [[soh/last_charging_capacity], ...], ... ]\n
        SOC y: [[[soc/last_charging_capacity], ...], ...]"""

        if(soh):
            y_indices = [
                DischargeCycleCols.CAPACITY if output_capacity else DischargeCycleCols.SOH
            ]

            train_raw_x, train_y = self.__get_whole_cycle_soh_x_y(
                self.train_discharge_cyc, self.x_cyc_indices, y_indices
            )
            test_raw_x, test_y = self.__get_whole_cycle_soh_x_y(
                self.test_discharge_cyc, self.x_cyc_indices, y_indices
            )
        else:
            y_indices = [
                DischargeCycleCols.CAPACITY if output_capacity else DischargeCycleCols.SOC
            ]

            train_raw_x, train_y = self.__get_whole_cycle_soc_x_y(
                self.train_discharge_cyc,
                self.x_cyc_indices,
                y_indices
            )

            test_raw_x, test_y = self.__get_whole_cycle_soc_x_y(
                self.test_discharge_cyc,
                self.x_cyc_indices,
                y_indices
            )

        train_scaled_x = self.__get_scaled_whole_cycle_x(
            train_raw_x, self.discharge_scalers)
        test_scaled_x = self.__get_scaled_whole_cycle_x(
            test_raw_x, self.discharge_scalers)

        train_x, test_x = self.__get_padded_whole_cycle(
            train_scaled_x, test_scaled_x)

        if(not soh):
            train_y, test_y = self.__get_padded_whole_cycle(train_y, test_y)

        train_raw_x, test_raw_x = self.__get_padded_whole_cycle(
            train_raw_x, test_raw_x)

        if(multiple_output and soh):
            # (SOH only) duplicate the y values to multiple steps for each cycle
            train_y = np.repeat(train_y[:, None, :], train_x.shape[1], axis=1)
            test_y = np.repeat(test_y[:, None, :], test_x.shape[1], axis=1)

        self.logger.info("Train x: %s, train y: %s | Test x: %s, test y: %s" %
                         (train_x.shape, train_y.shape, test_x.shape, test_y.shape))

        return (train_x, train_raw_x, train_y, test_x, test_raw_x, test_y)

    def __get_whole_cycle_soh_x_y(self, cyc, x_indices, y_indices):
        x = np.array(
            list(map(lambda data: data[:, x_indices].astype('float32'), cyc)), dtype=object
        )

        y = np.array(list(map(lambda data: data[0][y_indices].astype('float32'), cyc)))
        return (x, y)

    def __get_whole_cycle_soc_x_y(self, cyc, x_indices, y_indices):
        x = np.array(
            list(map(lambda data: data[:, x_indices].astype('float32'), cyc)), dtype=object
        )

        y = np.array(list(map(lambda data: data[:, y_indices].astype('float32'), cyc)), dtype=object)
        return (x, y)

    def __get_scaled_whole_cycle_x(self, x, scalers):
        def map_func(data):
            result = []
            for i in range(len(scalers)):
                result.append(scalers[i].transform(data[:, [i]]).flatten())
            return np.array(result).T
        #Modify by CHChen59
        return np.array(list(map(map_func, x)), dtype=object)
        #return np.array(list(map(map_func, x)))

    def __get_padded_whole_cycle(self, train, test):
        max_cycle_step_count = max(len(cycle)
                                   for cycle in np.append(train, test))
        required_step_count = max_cycle_step_count

        def padding_map_func(data):
            pad_width = ((0, required_step_count - len(data)), (0, 0))
            return np.pad(data, pad_width, 'constant', constant_values=0)

        train_padded = np.array(list(map(padding_map_func, train)))
        test_padded = np.array(list(map(padding_map_func, test)))

        return (train_padded, test_padded)

    def keep_only_capacity(self, y, is_multiple_output=False, is_grouped_multiple_step=False):
        if is_grouped_multiple_step:
            if is_multiple_output:
                new_y = y[:, :, :, 0]
            else:
                new_y = y[:, :, 0]
        else:
            if is_multiple_output:
                new_y = y[:, :, 0]
            else:
                new_y = y[:, 0]
        self.logger.info("New y: %s" % (new_y.shape,))
        return new_y
