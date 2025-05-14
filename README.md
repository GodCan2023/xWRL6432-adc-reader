# Real-time ADC Reader for xWRL6432 mmWave Radar via DCA1000

This Python package provides a **standalone** real-time ADC reader for the xWRL6432 mmWave radar sensor using the DCA1000 capture card — no installation of TI’s mmWave Studio required. It is especially useful for:

- Linux users who cannot run mmWave Studio  
- Developers building custom real-time signal-processing pipelines  

> **Note:** Texas Instruments officially supports only recording/playback/visualization via mmWave Studio. This module enables true real-time frame assembly and data access.

> **Don't have a DCA1000 capture card and don't need high data throughput?** Check out [this repo](https://github.com/loeens/mmwave-spi-ftdi-reader) which uses SPI and reads data after the first FFT.

## Features

- **Radar & DCA1000 Configuration**  
  Send CLI commands to both the xWRL6432 radar EVM and the DCA1000 from Python.  
- **Start/Stop Acquisition**  
  Simple API to begin and end streaming over the DCA1000 UDP interface.  
- **Robust Frame Assembly**  
  - Reorders out-of-order UDP packets  
  - Splits packets that cross frame boundaries  
  - Detects and discards incomplete frames  
- **Queue-based Output**  
  Push each assembled frame into a `queue.Queue` for downstream processing threads.  
- **Batch Recorder**  
  Record a fixed number of frames and either retrieve them in memory or save to a `.npz` file for offline analysis (e.g. in Jupyter Notebooks, example included).  
- **[OpenRadar](https://github.com/PreSenseRadar/OpenRadar) DSP Compatibility**  
  Works seamlessly with the OpenRadar DSP utilities for subsequent processing steps (e.g. range-doppler)

## Installation

1. Clone this repository and enter its directory:
    ```bash
    git clone https://github.com/loeens/xWRL6432-adc-reader.git
    cd xWRL6432-adc-reader
    ```
2. Install the package and its dependencies:
    ```bash
    pip install .
    ```

## Quick Start
### Radar EVM and DCA1000

### Code
```python
from queue import Queue
from xwrl6432_adc_reader import XWRL6432AdcReader

# 1) Create a thread-safe queue
data_queue = Queue()

# 2) Instantiate the reader
adc_reader = XWRL6432AdcReader(
    radar_serial_port="/dev/ttyACM1",
    radar_cfg_path="radar_config/iwrl6432.cfg",
    out_queue=data_queue
)

# 3) Start streaming in the background
adc_reader.start_acquisition()

# 4) In your processing loop:
try:
    while True:
        frame = data_queue.get()
        # → process your ADC frame here
except KeyboardInterrupt:
    pass

# 5) Clean up
adc_reader.stop_acquisition()
adc_reader.close()
```
A complete example is available in the `examples/` directory.

## Configuration File

The reader expects a TI-style radar configuration file (e.g. iwrl6432.cfg) that you would normally use with mmWave Studio. Place it in a known path and pass it to the constructor.

## Acknowledgements
A big thank you to:
- [**OpenRadar**](https://github.com/PreSenseRadar/OpenRadar): I copied and adapted the DCA1000 interface code from their `adc.py` module.
- **Texas Instruments**: For the specification documents and detailed packet-format documentation.