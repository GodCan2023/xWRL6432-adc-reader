"""
This example triggers the xWRL6432 (radar EVM) and the DCA1000 to stream ADC data.
A recorder object is created to create 100 frames. The program blocks until the 
100 frames are recorded, then they are written to an output file frame_dump.npz.
This file can then for example be loaded into a Jupyter Notebook (check out 
example.ipynb).
"""
from queue import Queue
from datetime import datetime
# Keep imports working although this file is iun subdir of the repo
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
from adc_reader.adc_reader import AdcReader
from adc_reader.utils.adc_recorder import ADCRecorder


# Create the queue which the reader will write the ADC data into
data_queue = Queue()

# Create xWRL6432AdcReader instance
adc_reader = AdcReader(
    # radar_serial_port="/dev/ttyACM1", # serial port to mmWave CLI (COM-port in Windows)
    radar_serial_port="COM16", # serial port to mmWave CLI (COM-port in Windows)
    radar_cfg_path="radar_config/iwrl6432_2.cfg", # path to radar EVM config file
    out_queue=data_queue
)

# Create recorder instance to record 100 frames
adc_recorder = ADCRecorder(
    input_queue=data_queue,
    num_frames=1024
)

try:
    # Start the aquisition (initializes radar EVM and DCA1000, then starts reading ADC data)
    adc_reader.start_acquisition()
    # Trigger the recorder and wait for it to complete (blocks)
    adc_recorder.start_recording()
    adc_recorder.wait_for_completion()
    # Export the recorded data to a .npz file
    adc_recorder.save_to_npz(
        file_path=f"examples/frame_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npz",
        config_metadata=adc_reader.get_radar_config()
    )
except KeyboardInterrupt:
    print("Stopping acquisition...")
finally:
    # Cleanup
    adc_reader.stop_acquisition()
    adc_reader.close()
    
