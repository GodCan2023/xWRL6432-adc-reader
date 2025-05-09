"""

"""
import threading
from multiprocessing import Queue
import serial

RADAR_CFG_FILE_PATH = "radar_config/iwrl6432.cfg"

class XWRL6432AdcReader(threading.Thread):
    def __init__(self, radar_serial_port: str, radar_cfg_path: str, out_queue: Queue):
        self.radar_serial_port = radar_serial_port
        self.out_queue = out_queue

        self._running = False

        # parse radar config into values
        num_chirps_per_frame, num_tx_ant, num_rx_ant, num_adc_samples = _parse_radar_config(radar_cfg_path)
        num_chirp_loops = chirps_per_frame / num_tx_ant
    
    def run(self):
        # trigger DCA1000 to start reading
        dca.start()
        # trigger radar via CLI to start chirping
        RadarCLI.start()
        
        while self._running:
            try:
                raw = dca.read()
                adc = self._decode_raw_data()
                self.out_queue.put(data)
            except Error:
                break

    def start(self):
        self._running = True
    
    def _parse_radar_config(self):
        # read fields from frameCfg and chirpComnCfg
        return chirps_per_frame, num_tx_ant, num_rx_ant, num_adc_samples
        
    def _init_radar(self, radar_serial_port):
        # configure
    
    def _init_dca1000(self):
        # create DCA1000 object
        # reset DCA1000
        # configure DCA1000
    
    def _decode_raw_data(self, raw):

    def _deswizzle(self, data)

    
    

    