import math
import struct
from pyModbusTCP.client import ModbusClient
import pandas as pd
import const
import time, datetime

class MfMbCtrl:
    """
    A class for controlling Modbus communication with MF-enabled Peripheries.
    """
    def __init__(self, _host_address: str, _modbus_port: int):
        """
        Initializes the MfMbCtrl class.

        :param _host_address: The host IP-Address of the MF-enabled Periphery.
        :param _modbus_port: The port number for Modbus communication.
        """
        self._host_address = _host_address
        self._modbus_port = _modbus_port
        self.client = ModbusClient(self._host_address, self._modbus_port, auto_open=True, auto_close=True)

    def read_data_set_from_mf(self,
                            _modbus_channel: int,
                            _slot: int,
                            _sub_slot: int,
                            _index: int,
                            _length: int):
        """
        Reads data set from the MF-enabled device.

        :param _modbus_channel: Modbus channel number.
        :param _slot: Slot number.
        :param _sub_slot: Sub-slot number.
        :param _index: Index of the data set.
        :param _length: Length of the data set to be read.

        :return: A list containing the read data set.
        """
        # create empty return list field
        mb_ds_data = []

        # check modbus channel number is in range (0 .. 10)
        if 0 <= _modbus_channel <= 10:

            # set channel registers dependent to the selected modbus channel number
            _currentChannelDistance = const.CHANNEL_DISTANCE * _modbus_channel
            _requestRegister = _currentChannelDistance + const.CHANNEL0_REQUEST_REGISTER
            _feedbackRegister = _currentChannelDistance + const.CHANNEL0_FEEDBACK_REGISTER
            _dataRegister = _currentChannelDistance + const.CHANNEL0_DATA_REGISTER
            _requestControl = const.DATASET_READ_CMD

            # calculate job data - especially for data set requests above 246 Bytes
            job_offset = 0
            _length = const.DATASET_MAX_LENGTH if _length > const.DATASET_MAX_LENGTH else _length
            job_length = const.DATASET_MAX_MF_JOB_LENGTH if _length > const.DATASET_MAX_MF_JOB_LENGTH else _length

            while job_length > 0:
                # send data set request
                _mb_ds_request = [_slot, _sub_slot, _index, _length, job_offset, job_length, _requestControl]
                _mb_response = self.client.write_multiple_registers(_requestRegister, _mb_ds_request)
                # scan for feedback until job is done
                _mb_ds_feedback = self.client.read_holding_registers(_feedbackRegister, const.FEEDBACK_REGISTER_LENGTH)
                while const.DATASET_FEEDBACK_STATE_DONE < _mb_ds_feedback[0] <= const.DATASET_FEEDBACK_STATE_BUSY:
                    _mb_ds_feedback = self.client.read_holding_registers(_feedbackRegister, const.FEEDBACK_REGISTER_LENGTH)
                if _mb_ds_feedback[0] == 0:
                    _job_length_register = math.ceil(job_length / 2)
                    _mb_ds_data = self.client.read_holding_registers(_dataRegister, _job_length_register)
                    
                    hex_mb_ds_data = [hex(num) for num in _mb_ds_data]
                    mb_ds_data.extend(hex_mb_ds_data)
                    # get next request details
                    job_offset += _mb_ds_feedback[2]
                    job_length = _mb_ds_feedback[1] - job_offset
                    job_length = const.DATASET_MAX_MF_JOB_LENGTH if job_length > const.DATASET_MAX_MF_JOB_LENGTH else job_length
                    _requestControl = 1
                else:
                    job_length = 0 
        return mb_ds_data

    def write_data_set_to_mf(self,
                            _modbus_channel: int,
                            _slot: int,
                            _sub_slot: int,
                            _index: int,
                            _length: int,
                            _mb_ds_data: list[int]):
        """
        Writes a data set to the MF-enabled device.

        :param _modbus_channel: Modbus channel number.
        :param _slot: Slot number.
        :param _sub_slot: Sub-slot number.
        :param _index: Index of the data set.
        :param _length: Length of the data set to be written.
        :param _mb_ds_data: List of integers representing the data to be written.

        :return: The feedback status indicating the write operation's completion.
        """
        # set channel registers dependent to the selected modbus channel number
        _currentChannelDistance = const.CHANNEL_DISTANCE * _modbus_channel
        _requestRegister = _currentChannelDistance + const.CHANNEL0_REQUEST_REGISTER
        _dataRegister = _currentChannelDistance + const.CHANNEL0_DATA_REGISTER
        _feedbackRegister = _currentChannelDistance + const.CHANNEL0_FEEDBACK_REGISTER
        _requestControl = const.DATASET_WRITE_CMD

        job_offset = 0
        job_length = _length

        _mb_ds_request = [_slot, _sub_slot, _index, _length, job_offset, job_length, _requestControl]

        _mb_response = self.client.write_multiple_registers(_dataRegister, _mb_ds_data)
        _mb_response = self.client.write_multiple_registers(_requestRegister, _mb_ds_request)
        _mb_ds_feedback = self.client.read_holding_registers(_feedbackRegister, const.FEEDBACK_REGISTER_LENGTH)
        while const.DATASET_FEEDBACK_STATE_DONE < _mb_ds_feedback[0] <= const.DATASET_FEEDBACK_STATE_BUSY:
                _mb_ds_feedback = self.client.read_holding_registers(_feedbackRegister, const.FEEDBACK_REGISTER_LENGTH)
        writing_done = _mb_ds_feedback[0]

        return writing_done

class Et200SpMf(MfMbCtrl):
    """
    This class represents an et200spMF device and provides methods for interacting with its properties.
    It inherits from the mfMbCtrl class.
    """
    def __init__(self, _host_address: str, _modbus_port: int, _iolink_master_ports: list):
        """
        Constructor for the et200spMF class.

        :param _host_address: The host IP-Address of the et200spMF device.
        :param _modbus_port: The port number for communication with the device.
        :param _iolink_master_ports: A list representing all ports of the used IO-Link Master.
        """
        super().__init__(_host_address, _modbus_port)
        self._iolink_master_ports = _iolink_master_ports

        # Create a DataFrame to store I&M data of modules
        device_im_data_columns = ['I&M - Information']
        device_im_data_columns.extend(const.MODULES)
        self.device_im_data = pd.DataFrame(data=None, index=None, columns=device_im_data_columns)
        self.device_im_data['I&M - Information'] = ['Article Number', 'Serial Number', 'HW Revision','FW Version']
        self.device_im_data.set_index('I&M - Information', inplace=True)

        # Create a DataFrame to store diagnostic data
        self.diagnose_data = pd.DataFrame(data=None, index=None, columns=['Slot', 'Submodule', 'Channel type', 'Channel number', 'Error code', 'Error message'])

        # Create a DataFrame to store information for IO-Link devices 
        iolink_devices_columns = ['Identification'] + self._iolink_master_ports
        self.iolink_devices = pd.DataFrame(data=None, index=None, columns=iolink_devices_columns)
        self.iolink_devices['Identification'] = ['Product Name', 'Vendor Name', 'DeviceID', 'VendorID']
        self.iolink_devices.set_index('Identification', inplace=True)

    def channel_direction(self, channel_properties):
        """
        Determine the channel type based on channel properties.

        :param channel_properties: The properties of the channel.

        :return: The determined channel type.
        """
        channel_direction = int(channel_properties[2:3])
        # Determine channel type based on channel direction
        if channel_direction == 0:
            channel_type = 'Herstellerspezifisch'
        elif channel_direction == 1:
            channel_type = 'Input'
        elif channel_direction == 2:
            channel_type = 'Output'
        elif channel_direction == 3:
            channel_type = 'Input/Output'
        elif 4 <= channel_direction <= 7:
            channel_type = 'Reserved'
        else:
            channel_type = None
        
        return channel_type
    
    def profinet_channel_err_type_coding(self): 
        """
        Define a DataFrame with error message mappings for Profinet channel errors.

        :return: A DataFrame with error messages mapped to error codes.
        """
        channelErrorType = pd.DataFrame(data=None, index=[hex(i) for i in range(0, 65536)], columns=['Error message'])
        channelErrorType.index.name = 'Value(hexadecimal)'
        #set Error messages
        channelErrorType.at['0x0', 'Error message'] = 'Unbekannter Fehler'
        channelErrorType.at['0x1', 'Error message'] = 'Kurzschluss'
        channelErrorType.at['0x2', 'Error message'] = 'Unterspannung'
        channelErrorType.at['0x3', 'Error message'] = 'Überspannung'
        channelErrorType.at['0x4', 'Error message'] = 'Überlast'
        channelErrorType.at['0x5', 'Error message'] = 'Übertemperatur'
        channelErrorType.at['0x6', 'Error message'] = 'Drahtbruch'
        channelErrorType.at['0x7', 'Error message'] = 'Oberer Grenzwert überschritten'
        channelErrorType.at['0x8', 'Error message'] = 'Unterer Grenzwert überschritten'
        channelErrorType.at['0x9', 'Error message'] = 'Fehler'
        for i in range(int(0xA), int(0xF)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] = 'Unbekannter Fehler'
        channelErrorType.at['0x10', 'Error message'] = 'Falsche Parametrierung'
        channelErrorType.at['0x11', 'Error message'] = 'Fehler Spannungsversorgung'
        channelErrorType.at['0x12', 'Error message'] = 'Sicherung ist durchgebrannt / hat ausgelöst'
        channelErrorType.at['0x13', 'Error message'] = 'Herstellerspezifisch'
        channelErrorType.at['0x14', 'Error message'] = 'Erdschluss'
        channelErrorType.at['0x15', 'Error message'] = 'Referenzpunkt nicht mehr vorhanden'
        channelErrorType.at['0x16', 'Error message'] = 'Abtastfehler'
        channelErrorType.at['0x17', 'Error message'] = 'Schwellwert über-/unterschritten'
        channelErrorType.at['0x18', 'Error message'] = 'Ausgang abgeschaltet'
        channelErrorType.at['0x19', 'Error message'] = 'sicherheitsrelevanter Fehler'
        channelErrorType.at['0x1a', 'Error message'] = 'Externer Fehler'
        for i in range(int(0x1B), int(0x1F)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] ='Herstellerspezifisch'
        for i in range(int(0x20), int(0xFF)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] = 'Standardprofile für alle Geräte (z.B. PROFIsafe)'
        for i in range(int(0x100), int(0x7FFF)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] = 'Herstellerspezifisch'
        channelErrorType.at['0x8000', 'Error message'] = 'Keine Datenübertragung möglich'
        channelErrorType.at['0x8001', 'Error message'] = 'Falsches Nachbarschaft'
        channelErrorType.at['0x8002', 'Error message'] = 'Redundanzverlust'
        channelErrorType.at['0x8003', 'Error message'] = 'Synchronisations-Verlust (geräteseitig)'
        channelErrorType.at['0x8004', 'Error message'] = 'Taktsynchronisations-Verlust (geräteseitig)'
        channelErrorType.at['0x8005', 'Error message'] = 'Querverkehr-Verbindungsfehler'
        channelErrorType.at['0x8006', 'Error message'] = 'Reserviert'
        channelErrorType.at['0x8007', 'Error message'] = 'Optische Übertragung nicht möglich'
        channelErrorType.at['0x8008', 'Error message'] = 'Probleme mit Netzwerkfunktion'
        channelErrorType.at['0x8009', 'Error message'] = 'Zeitgeber existiert nicht oder Probleme mit der Genauigkeit der Zeitbasis'
        for i in range(int(0x800A), int(0x8FFF)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] = 'Unbekannter Fehler'
        for i in range(int(0x9000), int(0x9FFF)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] = 'Profilspezifisch'
        for i in range(int(0xA000), int(0xFFFF)+1):
            channelErrorType.at[f'{hex(i)}', 'Error message'] = 'Unbekannter Fehler'

        return channelErrorType
    
    def get_device_im_data(self):
        """
        Fetches and stores the Identification & Maintenance (I&M) data for each module.

        This method retrieves I&M data such as Article Number, Serial Number, Hardware Revision, and Firmware Version
        for each module in the periphery. The fetched data is then stored in the device_im_data DataFrame.

        The DataFrame columns correspond to different modules, and rows contain I&M information categories.

        Note: Before calling this method, ensure that the device is properly initialized and connected.

        :return: None
        """
        for i in range(0,len(const.MODULES)):
            # Fetch I&M data from the module
            data = super().read_data_set_from_mf(0, i, 1, const.PROFINET_IM0_REGISTER, 60)
            # Extract and process I&M data from fetched data
            article_number = data[4:14]
            article_number_ascii = ''.join([bytes.fromhex(hex_value[2:]).decode('ASCII') for hex_value in article_number])

            serial_number = data[14:22]
            serial_number_ascii = ''.join([bytes.fromhex(hex_value[2:]).decode('ASCII') for hex_value in serial_number])

            hw_version = int(data[22][2:], 16)
            # Extract and process FW version
            fw_version_W1 = data[23][2:]
            fw_version_W2 = data[24][2:]
            fw_version_ascii = chr(int(fw_version_W1[:2], 16))
            im_sw_revision_functional_enhancement = int(fw_version_W1[2:], 16)
            if len(fw_version_W2) == 4:
                im_sw_revision_bug_fix = int(fw_version_W2[:2], 16)
                im_sw_revision_internal_change = int(fw_version_W2[2:], 16)
            elif len(fw_version_W2) == 3:
                im_sw_revision_bug_fix = int(fw_version_W2[:1], 16)
                im_sw_revision_internal_change = int(fw_version_W2[1:], 16)
            else:
                im_sw_revision_bug_fix = 0
                im_sw_revision_internal_change = int(fw_version_W2, 16)
            fw_version_ascii = f'{fw_version_ascii} {im_sw_revision_functional_enhancement}.{im_sw_revision_bug_fix}.{im_sw_revision_internal_change}'
            # Update the device_im_data DataFrame with fetched and processed I&M data
            self.device_im_data.at['Article Number', self.device_im_data.columns[i]] = article_number_ascii
            self.device_im_data.at['Serial Number', self.device_im_data.columns[i]] = serial_number_ascii
            self.device_im_data.at['HW Revision', self.device_im_data.columns[i]] = hw_version
            self.device_im_data.at['FW Version', self.device_im_data.columns[i]] = fw_version_ascii

    def get_diagnose(self):
        """
        Retrieve diagnostic data for the device's channels and store it in diagnose_data DataFrame.

        This method reads and processes diagnostic data for each channel with errors in the device.
        """
        # Clear existing diagnose data
        self.diagnose_data.drop(self.diagnose_data.index, inplace=True)
        # Retrieve error types mapping
        error_types = self.profinet_channel_err_type_coding()
        # Initialize error_number counter
        error_number = 0
        # Iterate through each module to retrieve diagnostic data
        for i in range(1,len(const.MODULES)+1):
            # Read diagnostic data from the device
            data = super().read_data_set_from_mf(0, i, 1, const.PROFINET_DIAGNOSE_REGISTER, 4096)
            try:
                # Calculate the number of channels with diagnosed errors
                number_of_channels_with_diagnose = int((int(data[1][2:], 16)-16)/6)
            except IndexError:
                # Handle the case when a submodule is not connected
                raise IndexError("Submodule not connected (Check if submodule is unplugged!)")

            # Process diagnostic data if there are channels with errors
            if number_of_channels_with_diagnose > 0:
                for j in range(0, number_of_channels_with_diagnose):
                    # Extract and store diagnostic information in diagnose_data DataFrame
                    self.diagnose_data.at[error_number, 'Slot'] = i
                    self.diagnose_data.at[error_number, 'Submodule'] = const.MODULES[i]
                    self.diagnose_data.at[error_number, 'Channel number'] = int(data[j*3+10][2:], 16)
                    self.diagnose_data.at[error_number, 'Channel type'] = self.channel_direction(data[j*3+11])
                    self.diagnose_data.at[error_number, 'Error code'] = data[j*3+12]
                    self.diagnose_data.at[error_number, 'Error message'] = error_types.at[data[j*3+12], 'Error message']
                    error_number+=1
            else:
                 # Skip processing if there are no channels with errors
                pass          
    
    def read_io_data(self):
        """
        Reads IO data from the IO-Link Master (where a temperature sensor - 3RS2 is connected), a DQ Module and a DI Module. These modules are attached to a MF-enabled Periphery. In the end, it processes the IO Data.

        :return: A tuple containing temperature, a list representing digital output status and another list representing digital input status.
        """
        # Read Temperature - IO-Link
        data = super().read_data_set_from_mf(0, 1, 1, const.PROFINET_INPUT_DATA_SUBMODULE_REGISTER, 50)
        temperature = int(data[7], 16)

        # Read DQ - Data
        data = super().read_data_set_from_mf(0, 2, 1, const.PROFINET_OUTPUT_DATA_SUBMODULE_REGISTER, 50)
        do = bin(int(data[6][5], 16))[2:]
        num_bits = 8
        padded_binary_string = do.zfill(num_bits)
        # Convert the binary string to a list of bits
        do = ['TRUE' if bit == "1" else 'FALSE' for bit in padded_binary_string]
        do.reverse()

        # Read DI - Data
        data = super().read_data_set_from_mf(0, 3, 1, const.PROFINET_INPUT_DATA_SUBMODULE_REGISTER, 50)
        di = bin(int(data[6][2], 16))[2:]
        num_bits = 8
        padded_binary_string = di.zfill(num_bits)
        # Convert the binary string to a list of bits
        di = ['TRUE' if bit == "1" else 'FALSE' for bit in padded_binary_string]
        di.reverse()

        return temperature, do, di

    def read_energy_meter_data(self, triggerEnergyCounter):
        """
        Reads energy meter data from the Energy Meter attached to a MF-enabled Periphery and processes it.

        :param triggerEnergyCounter: Flag indicating whether to reset the energy counter.

        :return: A tuple containing various meter data including current, voltage, power, energy counter,
            max current, max current timestamp, max voltage, and max voltage timestamp.
        """
        # ToDo: two versions of DS142 (version = 2/3), version can be found in Byte 0
        data = super().read_data_set_from_mf(0, 4, 1, 142, 150)

        # Extract CURRENT (A)
        hex_currentL1 = data[13:15]
        currentL1 = ''.join(hex_current[2:].zfill(4) for hex_current in hex_currentL1)
        currentL1 = struct.unpack('!f', bytes.fromhex(currentL1))[0] / 100  # Scaling factor of 0.01A

        # Extract VOLTAGE (V)
        voltageL1N = data[1:3]
        hex_voltageL1N = ''.join(hex_voltageL1N[2:].zfill(4) for hex_voltageL1N in voltageL1N)
        voltageL1N = struct.unpack('!f', bytes.fromhex(hex_voltageL1N))[0]

        # Extract ACTIVE POWER L1
        activePowerL1 = data[49:51]
        hex_activePowerL1 = ''.join(hex_activePowerL1[2:].zfill(4) for hex_activePowerL1 in activePowerL1)
        activePowerL1 = struct.unpack('!f', bytes.fromhex(hex_activePowerL1))[0]

        # Read total active energy L1 (Wh)
        data = super().read_data_set_from_mf(0, 4, 1, 147, 100)
        totalActiveEnergyL1 = data[20:24]
        hex_totalActiveEnergyL1 = ''.join(hex_totalActiveEnergyL1[2:].zfill(4) for hex_totalActiveEnergyL1 in totalActiveEnergyL1)
        totalActiveEnergyL1 = struct.unpack('!d', bytes.fromhex(hex_totalActiveEnergyL1))[0]

        if triggerEnergyCounter:
            self._startEnergyCounter = totalActiveEnergyL1
            energyCounter = 0
            print(True)
        else:
            self._lastEnergyCounter = totalActiveEnergyL1
            energyCounter = self._lastEnergyCounter - self._startEnergyCounter
            print(False)

        # Read Max Current + timestamp
        data = super().read_data_set_from_mf(0, 4, 1, 154, 500)
        maxCurrentL1 = data[49:51]  # Status 0x2 => No synchronization available
        hex_maxCurrentL1 = ''.join(hex_maxCurrentL1[2:].zfill(4) for hex_maxCurrentL1 in maxCurrentL1)
        maxCurrentL1 = struct.unpack('!f', bytes.fromhex(hex_maxCurrentL1))[0] / 100  # Scaling factor of 0.01A

        maxCurrentL1Timestamp = data[53:55]
        hex_maxCurrentL1Timestamp = ''.join(hex_maxCurrentL1Timestamp[2:].zfill(4) for hex_maxCurrentL1Timestamp in maxCurrentL1Timestamp)
        epochMaxCurrentL1Timestamp = struct.unpack('>I', bytes.fromhex(hex_maxCurrentL1Timestamp))[0]
        maxCurrentL1Timestamp = datetime.datetime.fromtimestamp(epochMaxCurrentL1Timestamp)

        # Read Max Voltage + Timestamp
        maxVoltageL1N = data[1:3]  # Status 0x2 => No synchronization available
        hex_maxVoltageL1N = ''.join(hex_maxVoltageL1N[2:].zfill(4) for hex_maxVoltageL1N in maxVoltageL1N)
        maxVoltageL1N = struct.unpack('!f', bytes.fromhex(hex_maxVoltageL1N))[0]

        maxVoltageL1NTimestamp = data[5:7]
        hex_maxVoltageL1NTimestamp = ''.join(hex_maxVoltageL1NTimestamp[2:].zfill(4) for hex_maxVoltageL1NTimestamp in maxVoltageL1NTimestamp)
        epochMaxVoltageL1NTimestamp = struct.unpack('>I', bytes.fromhex(hex_maxVoltageL1NTimestamp))[0]
        maxVoltageL1NTimestamp = datetime.datetime.fromtimestamp(epochMaxVoltageL1NTimestamp)

        return currentL1, voltageL1N, activePowerL1, energyCounter, maxCurrentL1, maxCurrentL1Timestamp, maxVoltageL1N, maxVoltageL1NTimestamp

    def liolink_device(self,
                _modbus_channel: int,
                _slot: int,
                _sub_slot: int,
                _port: int,
                _cap: int,
                _readWrite: int,
                _index: int,
                _subindex:int,
                _length: int,
                _writingRecord: list[int]):
        """
        Configures an IO-Link device using Modbus communication.
        The function supports you on the following tasks:
        - (Re)parameterization of a IO-Link Device
        - Diagnosis of a IO-Link Device
        - Execution of IO-Link port functions
        - Saving/Restoring IO-Link device parameters

        :param _modbus_channel: The Modbus channel to communicate with.
        :param _slot: The slot number of the IO-Link device.
        :param _sub_slot: The sub-slot number of the IO-Link device.
        :param _port: The port number of the IO-Link Master where the device is connected.
        :param _cap: Client Access Point to the IO-Link Master.
        :param _readWrite: 0 - Read dataset / 1 - Write Dataset
        :param _index: The index of the parameters.
        :param _subindex: The subindex of the parameter.
        :param _length: The length of data to be written/read. (1..116)
        :param _writingRecord: The data record which is written when a write request is triggered. 

        :return: The data read from or written to the IO-Link device.
        """
        #Prepare header (IO-Link Header) for dataset reading/writing.
        extFunctionNum_port = '0x080' + str(_port)
        extFunctionNum_port = int(extFunctionNum_port, 16)
        fiIndex = int('0xFE4A', 16) #FE4A
        _index = hex(_index)[2:].zfill(4)
        if _readWrite == 0:
            control_indexHighByte = '0x03' + _index[:2]
            iol_data = [0 for element in range(116)]
        elif _readWrite == 1:
            control_indexHighByte = '0x02' + _index[:2]
            iol_data = _writingRecord
        _length = _length + 4
        control_indexHighByte = int(control_indexHighByte, 16)
        indexLowByte_subindex = '0x' + _index[2:] + hex(_subindex)[2:].zfill(2)
        indexLowByte_subindex = int(indexLowByte_subindex, 16)
        _mb_ds_data= [extFunctionNum_port, fiIndex, control_indexHighByte, indexLowByte_subindex]
        _mb_ds_data.extend(iol_data)
        # Write data set to the Modbus device and handle response
        _writing_feedback = super().write_data_set_to_mf(_modbus_channel, _slot, _sub_slot, _cap, _length, _mb_ds_data)
        if _writing_feedback == 0:
            time.sleep(1)
            _mb_ds_data = super().read_data_set_from_mf(_modbus_channel, _slot, _sub_slot, _cap, _length)
        else:
            raise Exception("Writing failed with errcode: ", _writing_feedback)
        return _mb_ds_data

    def find_iolink_devices(self,
                    _modbus_channel: int,
                    _slot: int,
                    _sub_slot: int):
        """
        Finds and retrieves information about IO-Link devices connected to the IO-Link master.

        :param _modbus_channel: Modbus channel number to communicate with.
        :param _slot: The slot number of the IO-Link device.
        :param _sub_slot: The sub-slot number of the IO-Link device.
        """
        # Initialize default values for parameters
        _index = 0
        _subindex = 0
        _length = 20
        vendorID = []
        deviceID = []
        vendorName = []
        productID = []
        _port_number = len(self._iolink_master_ports)
        # Iterate through all available ports
        for i in range(_port_number):
            # Fetch direct parameters from the IO-Link device
            direct_parameters = self.liolink_device(_modbus_channel, _slot, _sub_slot, i+1, const.CAP, 0, _index, _subindex, _length, [])
            # Convert parameters to hexadecimal format and ensure proper formatting
            direct_parameters = ['0x' + param[2:].zfill(4) for param in direct_parameters]

            # Extract Vendor ID and Device ID from direct parameters
            hex_vendorID = '0x' + str(direct_parameters[7][4:]) + str(direct_parameters[8][2:4])
            vendorID.append(int(hex_vendorID, 16) if int(hex_vendorID, 16) != 0 else None)

            hex_deviceID = '0x' + str(direct_parameters[8][4:]) + str(direct_parameters[9][2:])
            deviceID.append(int(hex_deviceID, 16) if int(hex_deviceID, 16) != 0 else None)

            if vendorID[i] != None and deviceID[i] != None:
                # Fetch VendorName parameter
                _index = 16
                _length = 96
                vendorName = self.liolink_device(_modbus_channel, _slot, _sub_slot, i+1, const.CAP, 0, _index, _subindex, _length, []) #max length of this parameter is 96
                vendorName = vendorName[4:48]
                vendorName = self.remove_trailing_zeros(vendorName)
                vendorName = ['0x' + name[2:].zfill(4) for name in vendorName]
                vendorName_ascii = ''.join([bytes.fromhex(hex_value[2:]).decode('ASCII') for hex_value in vendorName])

                # Fetch ProductID parameter
                _index = 19
                productID = self.liolink_device(_modbus_channel, _slot, _sub_slot, i+1, const.CAP, 0, _index, _subindex, _length, [])
                productID = productID[4:48]
                productID = self.remove_trailing_zeros(productID)
                productID = ['0x' + id[2:].zfill(4) for id in productID]
                productID_ascii = ''.join([bytes.fromhex(hex_value[2:]).decode('ASCII') for hex_value in productID])

                # Update iolink_devices DataFrame with extracted information
                self.iolink_devices.at['Product Name', f'Port {i+1}'] = productID_ascii
                self.iolink_devices.at['Vendor Name', f'Port {i+1}'] = vendorName_ascii
            else:
                # If vendorID or deviceID is None, set corresponding DataFrame entries to None => No Device connected to the port
                self.iolink_devices.at['Product Name', f'Port {i+1}'] = None
                self.iolink_devices.at['Vendor Name', f'Port {i+1}'] = None
            
        # Update iolink_devices DataFrame with deviceID and vendorID    
        self.iolink_devices.loc['DeviceID', self._iolink_master_ports] = deviceID
        self.iolink_devices.loc['VendorID', self._iolink_master_ports] = vendorID

    def remove_trailing_zeros(self, array):
        lastNonZeroIndex = len(array) - 1

        # Find the index of the last non-zero element
        while lastNonZeroIndex >= 0 and array[lastNonZeroIndex] == '0x0':
            lastNonZeroIndex -= 1

        # Create a new array without trailing zeros
        new_array = array[:lastNonZeroIndex + 1]
        
        return new_array
    
class IOLinkMaster(MfMbCtrl):
    """
    This class represents an IO-Link Master and provides methods for interacting with IO-Link devices.
    It inherits from the mfMbCtrl class which is used for Modbus Communication.
    """
    def __init__(self, _host_address: str, _modbus_port: int, _iolink_master_ports: list):
        """
        Constructor for the iolink_master class.

        :param _host_address: The host IP-Address of the IO-Link Master.
        :param _modbus_port: The port number for communication with the IO-Link Master.
        :param _iolink_master_ports: A list representing all ports of the used IO-Link Master..
        """
        super().__init__(_host_address, _modbus_port)

        self._iolink_master_ports = _iolink_master_ports

        # Create a DataFrame to store IO-Link device information
        iolink_devices_columns = ['Identification'] + self._iolink_master_ports
        self.iolink_devices = pd.DataFrame(data=None, index=None, columns=iolink_devices_columns)
        self.iolink_devices['Identification'] = ['Product Name', 'Vendor Name', 'DeviceID', 'VendorID']
        self.iolink_devices.set_index('Identification', inplace=True)

    def liolink_device(self,
                _modbus_channel: int,
                _slot: int,
                _sub_slot: int,
                _port: int,
                _cap: int,
                _readWrite: int,
                _index: int,
                _subindex:int,
                _length: int,
                _writingRecord: list[int]):
        """
        Configures an IO-Link device using Modbus communication.
        The function supports you on the following tasks:
        - (Re)parameterization of a IO-Link Device
        - Diagnosis of a IO-Link Device
        - Execution of IO-Link port functions
        - Saving/Restoring IO-Link device parameters

        :param _modbus_channel: The Modbus channel to communicate with.
        :param _slot: The slot number of the IO-Link device.
        :param _sub_slot: The sub-slot number of the IO-Link device.
        :param _port: The port number of the IO-Link Master where the device is connected.
        :param _cap: Client Access Point to the IO-Link Master.
        :param _readWrite: 0 - Read dataset / 1 - Write Dataset
        :param _index: The index of the parameters.
        :param _subindex: The subindex of the parameter.
        :param _length: The length of data to be written/read. (1..116)
        :param _writingRecord: The data record which is written when a write request is triggered. 

        :return: The data read from or written to the IO-Link device.
        """
        #Prepare header (IO-Link Header) for dataset reading/writing.
        extFunctionNum_port = '0x080' + str(_port)
        extFunctionNum_port = int(extFunctionNum_port, 16)
        fiIndex = int('0xFE4A', 16) #FE4A
        _index = hex(_index)[2:].zfill(4)
        if _readWrite == 0:
            control_indexHighByte = '0x03' + _index[:2]
            iol_data = [0 for element in range(116)]
        elif _readWrite == 1:
            control_indexHighByte = '0x02' + _index[:2]
            iol_data = _writingRecord
        _length = _length + 4
        control_indexHighByte = int(control_indexHighByte, 16)
        indexLowByte_subindex = '0x' + _index[2:] + hex(_subindex)[2:].zfill(2)
        indexLowByte_subindex = int(indexLowByte_subindex, 16)
        _mb_ds_data= [extFunctionNum_port, fiIndex, control_indexHighByte, indexLowByte_subindex]
        _mb_ds_data.extend(iol_data)
        # Write data set to the Modbus device and handle response
        _writing_feedback = super().write_data_set_to_mf(_modbus_channel, _slot, _sub_slot, _cap, _length, _mb_ds_data)
        if _writing_feedback == 0:
            time.sleep(1)
            _mb_ds_data = super().read_data_set_from_mf(_modbus_channel, _slot, _sub_slot, _cap, _length)
        else:
            raise Exception("Writing failed with errcode: ", _writing_feedback)
        return _mb_ds_data

    def find_iolink_devices(self,
                    _modbus_channel: int,
                    _slot: int,
                    _sub_slot: int):
        """
        Finds and retrieves information about IO-Link devices connected to the IO-Link master.

        :param _modbus_channel: Modbus channel number to communicate with.
        :param _slot: The slot number of the IO-Link device.
        :param _sub_slot: The sub-slot number of the IO-Link device.
        """
        # Initialize default values for parameters
        _index = 0
        _subindex = 0
        _length = 20
        vendorID = []
        deviceID = []
        vendorName = []
        productID = []
        _port_number = len(self._iolink_master_ports)

        # Iterate through all available ports
        for i in range(_port_number):
            # Fetch direct parameters from the IO-Link device
            direct_parameters = self.liolink_device(_modbus_channel, _slot, _sub_slot, i+1, const.CAP, 0, _index, _subindex, _length, [])
            # Convert parameters to hexadecimal format and ensure proper formatting
            direct_parameters = ['0x' + param[2:].zfill(4) for param in direct_parameters]

            # Extract Vendor ID and Device ID from direct parameters
            hex_vendorID = '0x' + str(direct_parameters[7][4:]) + str(direct_parameters[8][2:4])
            vendorID.append(int(hex_vendorID, 16) if int(hex_vendorID, 16) != 0 else None)

            hex_deviceID = '0x' + str(direct_parameters[8][4:]) + str(direct_parameters[9][2:])
            deviceID.append(int(hex_deviceID, 16) if int(hex_deviceID, 16) != 0 else None)

            if vendorID[i] != None and deviceID[i] != None:
                # Fetch VendorName parameter
                _index = 16
                _length = 96
                vendorName = self.liolink_device(_modbus_channel, _slot, _sub_slot, i+1, const.CAP, 0, _index, _subindex, _length, []) #max length of this parameter is 96
                vendorName = vendorName[4:48]
                vendorName = self.remove_trailing_zeros(vendorName)
                vendorName = ['0x' + name[2:].zfill(4) for name in vendorName]
                vendorName_ascii = ''.join([bytes.fromhex(hex_value[2:]).decode('ASCII') for hex_value in vendorName])

                # Fetch ProductID parameter
                _index = 19
                productID = self.liolink_device(_modbus_channel, _slot, _sub_slot, i+1, const.CAP, 0, _index, _subindex, _length, [])
                productID = productID[4:48]
                productID = self.remove_trailing_zeros(productID)
                productID = ['0x' + id[2:].zfill(4) for id in productID]
                productID_ascii = ''.join([bytes.fromhex(hex_value[2:]).decode('ASCII') for hex_value in productID])

                # Update iolink_devices DataFrame with extracted information
                self.iolink_devices.at['Product Name', f'Port {i+1}'] = productID_ascii
                self.iolink_devices.at['Vendor Name', f'Port {i+1}'] = vendorName_ascii
            else:
                # If vendorID or deviceID is None, set corresponding DataFrame entries to None => No Device connected to the port
                self.iolink_devices.at['Product Name', f'Port {i+1}'] = None
                self.iolink_devices.at['Vendor Name', f'Port {i+1}'] = None
        
        # Update iolink_devices DataFrame with deviceID and vendorID
        self.iolink_devices.loc['DeviceID', self._iolink_master_ports] = deviceID
        self.iolink_devices.loc['VendorID', self._iolink_master_ports] = vendorID

    def read_io_data(self):
        """
        Reads and returns temperature data from an IO-Link device (Temperature monitoring relay - 3RS2) connected in port 2.

        :return: Temperature value.
        """
        # Read IO-Link device data
        data = self.liolink_device(0, 0, 1, 4, const.CAP, 0, 40, 0, 50, [])
        # Extract temperature value
        temperature = int(data[5], 16)

        return temperature

    def remove_trailing_zeros(self, array):
        lastNonZeroIndex = len(array) - 1

        # Find the index of the last non-zero element
        while lastNonZeroIndex >= 0 and array[lastNonZeroIndex] == '0x0':
            lastNonZeroIndex -= 1

        # Create a new array without trailing zeros
        new_array = array[:lastNonZeroIndex + 1]
        
        return new_array