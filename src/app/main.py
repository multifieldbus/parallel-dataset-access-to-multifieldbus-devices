from datetime import datetime
from bokeh.io import output_file, curdoc
from bokeh.models import ColumnDataSource, TableColumn, Button, Div, DatetimeTickFormatter, Tabs, TabPanel, HoverTool
from bokeh.models.widgets import DataTable
from bokeh.layouts import row, column
from bokeh.plotting import figure
import const
from mfMb import MfMbCtrl, IOLinkMaster, Et200SpMf

def ui_et200mf(mfMbClient):
    """
    A function to create and update the UI for ET 200SP IM MF Modul
    """
    # Creating a data source and columns for the Diagnose table
    diagnose_source = ColumnDataSource(data={})
    diagnose_columns = [TableColumn(field='Slot', title='Slot'), 
               TableColumn(field='Submodule', title='Submodule'), 
               TableColumn(field='Channel number', title='Channel number'), 
               TableColumn(field='Channel type', title='Channel type'), 
               TableColumn(field='Error code', title='Error code'), 
               TableColumn(field='Error message', title='Error message')]
    diagnose_table = DataTable(source=diagnose_source, columns=diagnose_columns, index_position=None, width=800, height=450)

    # Fetching and displaying I&M data for the MF Station
    mfMbClient.get_device_im_data()
    device_im_data_source = ColumnDataSource(data=mfMbClient.device_im_data)
    im_data_columns = [TableColumn(field='I&M - Information', title='I&M - Information')]
    for device in const.MODULES:
        im_data_column = TableColumn(field=device, title=device)
        im_data_columns.append(im_data_column)
    im_data_table = DataTable(source=device_im_data_source, columns=im_data_columns, index_position=None, width=800, height=450)
    im_data_tab = TabPanel(child=im_data_table, title="MF Station")

    # Finding IO-Link devices and displaying their identification data
    mfMbClient.find_iolink_devices(0, 1, 1)
    iolink_devices_im_data_source = ColumnDataSource(data={})
    iolink_devices_im_data_columns = [TableColumn(field='Identification', title='Identification')]
    for device in const.PORTS:
        iolink_devices_im_data_column = TableColumn(field=device, title=device)
        iolink_devices_im_data_columns.append(iolink_devices_im_data_column)
    iolink_devices_im_data_table = DataTable(source=iolink_devices_im_data_source, columns=iolink_devices_im_data_columns, index_position=None, width=800, height=450)
    iolink_devices_im_tab = TabPanel(child=iolink_devices_im_data_table, title="CM 4xIO-Link")

    # Creating tabs for displaying information
    information_tabs = Tabs(tabs=[im_data_tab, iolink_devices_im_tab])

    # Function to update data when the 'Update' button is clicked
    def update_data():
        mfMbClient.get_diagnose()
        diagnose_data = mfMbClient.diagnose_data
        diagnose_source.data = dict(ColumnDataSource(diagnose_data).data)
        mfMbClient.find_iolink_devices(0, 1, 1)
        iolink_devices_im_data_source.data = dict(ColumnDataSource(data=mfMbClient.iolink_devices).data)
    
    # Initial data update and button setup
    update_data()
    update = Button(label='Update', button_type='success', width=100, height=50)
    update.on_click(update_data)

    PLOT_WIDTH = 800
    PLOT_HEIGHT = 400

    # Create a new Bokeh figure
    temperature_figure = figure(width=PLOT_WIDTH, height=PLOT_HEIGHT,
            x_axis_type="datetime", tools="xpan", toolbar_location=None)
    temperature_figure.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S",
    minutes="%H:%M:%S",
    minsec="%H:%M:%S")
    
    # Temperature - Figure
    temperature_source = ColumnDataSource(data=dict(time=[], value=[]))
    temperature_figure.line(x='time', y='value', line_color='blue', source=temperature_source)
    temperature_figure.title.text = "Temperature"
    temperature_figure.title.align = 'center'
    temperature_tab = TabPanel(child=temperature_figure, title="IO-Link Data")
    # Format the tooltip
    tooltips = [('Temperature', ' @value °C')]
    temperature_figure.add_tools(HoverTool(tooltips=tooltips))
    # DI/DQ - Figure
    di_dq_source = ColumnDataSource({})
    di_dq_columns = [TableColumn(field='Channel', title='Channel'),
                     TableColumn(field='DQ', title='DQ'),
                     TableColumn(field='DI', title='DI')]
    di_dq_table = DataTable(source=di_dq_source, columns=di_dq_columns, index_position=None, width=PLOT_WIDTH, height=PLOT_HEIGHT)
    di_dq_tab = TabPanel(child=di_dq_table, title="DI/DQ Data")

    io_update_time=Div(text='', styles={'text-align': 'center'}, width=810, height=15)

    #Initialize
    currentL1, voltageL1N, activePowerL1, activeEnergyOutflowL1, maxCurrentL1, maxCurrentL1Timestamp, maxVoltageL1N, maxVoltageL1NTimestamp  = mfMbClient.read_energy_meter_data(True)

    #Create figure for Energy Data
    currentL1_figure = figure(width=PLOT_WIDTH, height=PLOT_HEIGHT,
            x_axis_type="datetime", tools="xpan", toolbar_location=None)
    currentL1_figure.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S",
    minutes="%H:%M:%S",
    minsec="%H:%M:%S")

    currentL1_source = ColumnDataSource(data=dict(time=[], value=[]))
    currentL1_figure.line(x='time', y='value', line_color='blue', source=currentL1_source)
    currentL1_figure.title.text = "Current L1"
    currentL1_figure.title.align = 'center'
    currentL1_tab = TabPanel(child=currentL1_figure, title="Current L1")
    tooltips = [('Current L1', ' @value A')]
    currentL1_figure.add_tools(HoverTool(tooltips=tooltips))

    voltageL1N_figure = figure(width=PLOT_WIDTH, height=PLOT_HEIGHT,
            x_axis_type="datetime", tools="xpan", toolbar_location=None)
    voltageL1N_figure.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S",
    minutes="%H:%M:%S",
    minsec="%H:%M:%S")

    voltageL1N_source = ColumnDataSource(data=dict(time=[], value=[]))
    voltageL1N_figure.line(x='time', y='value', line_color='blue', source=voltageL1N_source)
    voltageL1N_figure.title.text = "Voltage L1-N"
    voltageL1N_figure.title.align = 'center'
    voltageL1N_tab = TabPanel(child=voltageL1N_figure, title="Voltage L1-N")
    tooltips = [('Voltage L1-N', ' @value V')]
    voltageL1N_figure.add_tools(HoverTool(tooltips=tooltips))

    activePowerL1_figure = figure(width=PLOT_WIDTH, height=PLOT_HEIGHT,
            x_axis_type="datetime", tools="xpan", toolbar_location=None)
    activePowerL1_figure.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S",
    minutes="%H:%M:%S",
    minsec="%H:%M:%S")

    activePowerL1_source = ColumnDataSource(data=dict(time=[], value=[]))
    activePowerL1_figure.line(x='time', y='value', line_color='blue', source=activePowerL1_source)
    activePowerL1_figure.title.text = "Active power L1"
    activePowerL1_figure.title.align = 'center'
    activePowerL1_tab = TabPanel(child=activePowerL1_figure, title="Active power L1")
    tooltips = [('Active power L1', ' @value W')]
    activePowerL1_figure.add_tools(HoverTool(tooltips=tooltips))

    
    energyCounterL1_figure = figure(width=PLOT_WIDTH, height=PLOT_HEIGHT,
            x_axis_type="datetime", tools="xpan", toolbar_location=None)
    energyCounterL1_figure.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S",
    minutes="%H:%M:%S",
    minsec="%H:%M:%S")

    energyCounterL1_source = ColumnDataSource(data=dict(time=[], value=[]))
    energyCounterL1_figure.line(x='time', y='value', line_color='blue', source=energyCounterL1_source)
    energyCounterL1_figure.title.text = "Energy Counter L1"
    energyCounterL1_figure.title.align = 'center'
    tooltips = [('Energy Counter L1', ' @value Wh')]
    energyCounterL1_figure.add_tools(HoverTool(tooltips=tooltips))

    # Function to handle the "Reset Energy Counter L1" button click event
    def reset_EnergyCounterL1_clicked():
        # Disable the button to prevent multiple clicks during database processing
        curdoc().add_next_tick_callback(lambda : setattr(resetEnergyCounterL1, 'disabled', True))
        print("loop entered.")
        
        # Function to reset the energy counter for L1
        def reset_EnergyCounterL1():
            # Read energy meter data and perform reset
            currentL1, voltageL1N, activePowerL1, energyCounterL1, maxCurrentL1, maxCurrentL1Timestamp, maxVoltageL1N, maxVoltageL1NTimestamp  = mfMbClient.read_energy_meter_data(True)
            print("loop entered. 2")
        
        # Schedule the reset_EnergyCounterL1 function to run on the next tick
        curdoc().add_next_tick_callback(reset_EnergyCounterL1)
        # Simulate a long database query processing
        curdoc().add_next_tick_callback(lambda : setattr(resetEnergyCounterL1, 'disabled', False))  
    
    # Create the "Reset Energy Counter L1" button and set its click event handler
    resetEnergyCounterL1 = Button(label='Reset Energy Counter L1', button_type='success', width=100, height=50)
    resetEnergyCounterL1.on_click(reset_EnergyCounterL1_clicked)

    # Create a tab for displaying energy counter L1 with a reset button
    energyCounterL1_tab = TabPanel(child=row(children=[energyCounterL1_figure, resetEnergyCounterL1]), title="Energy Counter L1")

    # Create Div elements for displaying max current and max voltage information
    maxCurrentL1_text=Div(text='', styles={'text-align': 'center'}, width=810, height=15)
    maxVoltageL1N_text=Div(text='', styles={'text-align': 'center'}, width=810, height=15)

    # Function to read data periodically and update visualizations
    def read_periodically():
        # Read I/O data
        temperature, do, di = mfMbClient.read_io_data()

        # Update temperature data
        new_temperature_data = dict(time=[datetime.now()], value=[temperature])
        temperature_source.stream(new_temperature_data, rollover=400)
        
        # Update digital input and output data
        di_dq_source.data = {'Channel': [1,2,3,4,5,6,7,8], 'DQ': do, 'DI': di}
        io_update_time.text = f'Update time: {datetime.now()}'

        # Read energy meter data
        currentL1, voltageL1N, activePowerL1, energyCounterL1, maxCurrentL1, maxCurrentL1Timestamp, maxVoltageL1N, maxVoltageL1NTimestamp  = mfMbClient.read_energy_meter_data(False)

        # Update visualizations for current, voltage, power, and energy counter
        new_currentL1_data = dict(time=[datetime.now()], value=[currentL1])
        currentL1_source.stream(new_currentL1_data, rollover=400)

        new_voltageL1N_data = dict(time=[datetime.now()], value=[voltageL1N])
        voltageL1N_source.stream(new_voltageL1N_data, rollover=400)

        new_activePowerL1_data = dict(time=[datetime.now()], value=[activePowerL1])
        activePowerL1_source.stream(new_activePowerL1_data, rollover=400)

        new_energyCounterL1_data = dict(time=[datetime.now()], value=[energyCounterL1])
        energyCounterL1_source.stream(new_energyCounterL1_data, rollover=400)

        # Update text display for max current and max voltage information
        maxCurrentL1_text.text = f'Max Current: {maxCurrentL1}A, Timestamp: {maxCurrentL1Timestamp}'
        maxVoltageL1N_text.text = f'Max Voltage: {maxVoltageL1N}V, Timestamp: {maxVoltageL1NTimestamp}'

    # Create tabs for I/O data and energy data visualizations
    io_data_tabs = Tabs(tabs=[temperature_tab, di_dq_tab])
    energy_data_tabs = Tabs(tabs=[currentL1_tab, voltageL1N_tab, activePowerL1_tab, energyCounterL1_tab])

    # Specify the output file for the HTML document
    output_file('diagnose.html')

    # Titles for the Diagnose and Identification & Maintenance (I&M) sections
    diagnose_title = '<h1 style="font-size: 18px; font-weight: bold;">Diagnose</h1>'
    im_title = '<h1 style="font-size: 18px; font-weight: bold;">Identification and Maintenance (I&M)</h1>'

    # Create the main layout structure using rows and columns
    layout = row(column(
        children=[row(children=[Div(text=diagnose_title, styles={'text-align': 'center'} ,width=600, height=50), update], sizing_mode='scale_width'),
                  diagnose_table, 
                  Div(text=im_title, styles={'text-align': 'center'} ,width=810, height=50), 
                  information_tabs], sizing_mode='scale_height'), 
                  column(children=[io_data_tabs, energy_data_tabs, maxCurrentL1_text, maxVoltageL1N_text, io_update_time]))

    # Set up periodic callback for data updates
    curdoc().add_periodic_callback(read_periodically, 1500)

    # Create a tab layout for the entire page
    tab_layout = TabPanel(child=layout, title="ET200SP MF")

    # Return the tab layout to be displayed
    return tab_layout

def ui_et200ecopn(mfMbClient):
    """
    A function to create and update the UI for ET 200eco PN Modul
    """
    # Finding IO-Link devices and displaying their identification data
    mfMbClient.find_iolink_devices(0, 0, 1)
    ecopn_iolink_devices_im_data_source = ColumnDataSource(data=mfMbClient.iolink_devices)
    ecopn_iolink_devices_im_data_columns = [TableColumn(field='Identification', title='Identification')]
    for device in const.PORTS_ECOPN:
        ecopn_iolink_devices_im_data_column = TableColumn(field=device, title=device)
        ecopn_iolink_devices_im_data_columns.append(ecopn_iolink_devices_im_data_column)
    ecopn_iolink_devices_im_data_table = DataTable(source=ecopn_iolink_devices_im_data_source, columns=ecopn_iolink_devices_im_data_columns, index_position=None, width=800, height=450)

    PLOT_WIDTH = 800
    PLOT_HEIGHT = 400

    # Create a new Bokeh figure
    ecopn_temperature_figure = figure(width=PLOT_WIDTH, height=PLOT_HEIGHT,
            x_axis_type="datetime", tools="xpan", toolbar_location=None)
    ecopn_temperature_figure.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S",
    minutes="%H:%M:%S",
    minsec="%H:%M:%S")
    
    # Temperature - Figure
    ecopn_temperature_source = ColumnDataSource(data=dict(time=[], value=[]))
    ecopn_temperature_figure.line(x='time', y='value', line_color='blue', source=ecopn_temperature_source)
    ecopn_temperature_figure.title.text = "Temperature"
    ecopn_temperature_figure.title.align = 'center'
    # Format the tooltip
    tooltips = [('Temperature', ' @value °C')]
    ecopn_temperature_figure.add_tools(HoverTool(tooltips=tooltips))

    io_update_time=Div(text='', styles={'text-align': 'center'}, width=810, height=50)

    # Function to read data periodically and update visualizations
    def read_periodically():
        # Read I/O data
        temperature = mfMbClient.read_io_data()
        # Update temperature data
        new_temperature_data = dict(time=[datetime.now()], value=[temperature])
        ecopn_temperature_source.stream(new_temperature_data, rollover=400)

        io_update_time.text = f'Update time: {datetime.now()}'

    # Create the main layout structure using rows and columns
    layout = row(children= [ecopn_iolink_devices_im_data_table, column(children=[ecopn_temperature_figure, io_update_time])])

    # Create a tab layout for the entire page
    ecopn_iolink_devices_im_tab = TabPanel(child=layout, title="ET200ecoPN")

    # Set up periodic callback for data updates
    curdoc().add_periodic_callback(read_periodically, 1000)

    # Return the tab layout to be displayed
    return ecopn_iolink_devices_im_tab

def ui(layout1, layout2):
    """
    A function to display two tabs (e.g. UI for ET 200SP IM MF and UI for ET 200eco PN)
    """
    tabs = Tabs(tabs=[layout1, layout2])
    curdoc().add_root(tabs)
    curdoc().title = 'Multifieldbus'

def main():
    # Define connection with ET 200SP IM MF and ET 200eco PN Modules
    mfMbClient_MF = Et200SpMf(_host_address=const.IP_ADDRESS_MF, _modbus_port=const.MULTIFIELDBUS_DEFAULT_PORT, _iolink_master_ports=const.PORTS)
    mfMbClient_ECOPN = IOLinkMaster(_host_address=const.IP_ADDRESS_ECOPN, _modbus_port=const.MULTIFIELDBUS_DEFAULT_PORT, _iolink_master_ports=const.PORTS_ECOPN)
    
    # Create UIs for ET 200SP IM MF and ET 200eco PN Module in form of Tabs
    mf_ui = ui_et200mf(mfMbClient_MF)
    ecopn_ui = ui_et200ecopn(mfMbClient_ECOPN)
    
    #Display/Merge the two UIs in form of tabs in one page
    ui(mf_ui, ecopn_ui)

# Required for the Bokeh Server to work
main()

if __name__ == "__main__":
    main()
