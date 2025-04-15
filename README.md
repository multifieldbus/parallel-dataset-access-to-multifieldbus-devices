# Parallel dataset access to multifieldbus devices
The primary aim of this application is to establish a non-disruptive system or infrastructure in industrial automation. This system is designed for IT level to gather supplementary information from Field / Periphery Level such as automation component details, usage history, hardware, firmware status, and machine conditions (e.g., temperature, vibration, energy consumption etc.). 

The key focus is on ensuring that this data collection does not impact the core automation task. The intention is to build a framework that remains separate from the automation process, preventing any unnecessary load on the PLC. This infrastructure sets the stage for potential future IT applications, showcasing the diverse applications of the data without directly impacting the existing automation workflow. 

The approach outlined in this example demonstrates a method to extract additional information from the field and peripheral level without requiring adjustments or expansions to the existing PROFINET-based automation solution. The key advantage is that neither the control program nor the fundamental hardware structure needs to be modified. In the optimal scenario, it suffices to replace the interface module of the utilized SIMATIC peripheral station.

![Network Overview](docs/Network.png?raw=true)

![Concept (Part 1)](docs/Concept_1.png?raw=true)

![Concept (Part 2)](docs/Concept_2.png?raw=true)

## How to use the solution / application example

This application lays the groundwork of potential future IT applications. It offers a library (found in [mfMb.py](app/mfMb.py)) with 3 classes (MfMbCtrl, Et200SpMf, IOLinkMaster) which are used for communication with MultiFieldbus devices. In the class MfMbCtrl, the 3-staged Communication Methods for writing DS to / reading DS from MultiFieldbus Devices. This class shall not be changed/modified. 

The other two classes, Et200SpMF and IOLinkMaster, can be further developed or converted to another programming language depending on the specific requirements of the user. Both inherit the class MfMbCtrl and use its functions for communication with MF Devices. They are both depended on the hardware setup (e.g. ET 200SP IM MF on the submodules like DI, DO etc. and their order in the rack). Therefore some of the functions in this library have to be modified depending on the user use case or hardware setup.

In the const.py file, declarations include constants such as IP addresses, datasets/data records for specific purposes, a list of ports for IO-Link Masters etc. Some of these information can be edited depending on the user / device specification (e.g. IP-Address, naming of the elements of the port / module lists etc). It is not advised to change the dataset constants since they are based on the hardware setup used and on the PROFINET Specification.

First step to running the code, is to install all the necessary libraries. All the libraries can be found in [requirements.txt](app/requirements.txt) file. They can be installed directly by running this on the terminal:
```
$ pip install -r requirements.txt
```
Additionally, an application example or an example on how to use these classes can be found in [main.py](app/main.py) file. Here is an UI programmed with bokeh which runs in a bokeh server. The web-application can run by running this line on the terminal:
```
$ bokeh serve --show main.py
```
Overall, this application only shows a concept on IT <--> Field/Periphery Level Communication independent of the Control Level <--> Field/Periphery Level Communication. It showcases what is achievable and outlines potential execution methods.


