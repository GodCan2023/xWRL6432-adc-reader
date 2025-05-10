"""

"""
import threading
from multiprocessing import Queue
import serial
from pathlib import Path

RADAR_CFG_FILE_PATH = "radar_config/iwrl6432.cfg"

class XWRL6432AdcReader(threading.Thread):
    def __init__(self, radar_serial_port: str, radar_cfg_path: str, out_queue: Queue):
        super().__init__(daemon=True)

        self.out_queue = out_queue
        self._running = False # Don't start running immediately
        self.radar_cfg_path = Path(radar_cfg_path)

        self.cli = None
        self.dca = None
        
        # Ensure supplied radar_cfg_path exists
        if not self.radar_cfg_path.is_file():
            raise FileNotFoundError(f"Config file not found: {self.radar_cfg_path}")
        if self.radar_cfg_path.suffix != '.cfg': 
            raise ValueError("Supplied config file must be of type/format .cfg")

        # Parse radar config into values
        try:
            self.num_chirps_per_frame, self.num_tx_ant, self.num_rx_ant, self.num_adc_samples = self._parse_radar_config(self.radar_cfg_path)
            
            if self.num_tx_ant <= 0:
                raise ValueError("Parsed num_tx_ant is zero or negative.")
            self.num_chirp_loops = self.num_chirps_per_frame // self.num_tx_ant
            
            num_chirps_per_frame, num_tx_ant, num_rx_ant, num_adc_samples = self.num_chirps_per_frame, self.num_tx_ant, self.num_rx_ant, self.num_adc_samples
            print(f"num_chirps_per_frame: {num_chirps_per_frame}, num_tx_ant: {num_tx_ant}, \
            \num_rx_ant: {num_rx_ant}, num_adc_samples: {num_adc_samples}")
        except Exception as e:
            print(f"Failed to parse config: {e}")
            raise
        
    def run(self):
        if not self._running or self.dca is None or self.cli is None:
            print("ADC Reader: Run condition not met (not running or DCA/Radar CLI not initialized). Exiting thread.")
            return

        print("ADC Reader thread: Starting data acquisition loop.")
        while self._running:
            try:
                raw_frame = self.dca.read()
                if raw_frame:
                    adc_data = self._decode_raw_data(raw_frame)
                    self.out_queue.put(adc_data)
                elif self._running:
                    print("ADC Reader thread: No data from DCA read")
                    raise RuntimeError("No data from DCA read while reader was active")
                else: 
                    break 
            except Exception as e: 
                if self._running: 
                    print(f"ADC Reader thread: Error during data read/process: {e}")
                break
        print("ADC Reader thread: Data acquisition loop finished.")

    def start_acquisition(self):
        try:
            if self.cli is None or self.dca is None:
                self._init_hardware()
            
            if self.cli is None or self.dca is None:
                print("Cannot start acquisition: Hardware initialization failed.")
                return

            self.dca.start_stream()
            self.cli.send_start_cmd()
            self._running = True
            super().start()
            print("ADC Reader: Acquisition started.")
        except Exception as e:
            print(f"ADC Reader: Failed to start acquisition: {e}")
    
    def stop_acquisition(self, wait_for_thread=True, timeout=2.0):
        print("ADC Reader: Stopping acquisition...")
        self._running = False

        if self.cli:
            try:
                self.cli.send_stop_cmd()
            except Exception as e:
                print(f"ADC Reader: Error sending CLI stop command: {e}")
        if self.dca:
            try:
                self.dca.stop_stream()
            except Exception as e:
                print(f"ADC Reader: Error stopping DCA stream: {e}")

        if wait_for_thread and self.is_alive():
            print(f"ADC Reader: Waiting for thread to finish (timeout: {timeout}s)...")
            self.join(timeout) 
            if self.is_alive():
                print("ADC Reader: Thread did not terminate in time.")
        print("ADC Reader: Acquisition stopped.")
    
    def close(self):
        if self.cli:
            self.cli.close()
        if self.dca:
            self.dca.close()

    def _init_hardware(self):
        if self.cli is not None and self.dca is not None:
            print("Hardware already initialized.")
            return

        try:
            self.cli = RadarCLI(self.radar_serial_port)
            self.cli.send_config(self.radar_cfg_path)
            print("Radar EVM initialized and configured.")
        except Exception as e:
            print(f"Failed to configure radar: {e}")
            self.cli = None
            raise
        
        try:
            self.dca = DCA1000(self.num_chirp_loops, self.num_rx_ant, self.num_tx_ant, self.num_adc_samples)
            self.dca.reset()
            self.dca.configure()
            print("DCA1000 initialized and configured.")
        except Exception as e:
            print(f"Failed to configure DCA1000: {e}")
            self.dca = None
            raise
    
    
    @staticmethod
    def _parse_radar_config(config_path: Path):
        chirps_per_frame, num_tx_ant, num_rx_ant, num_adc_samples = 0
        num_chirps_per_burst, num_bursts_per_frame = 0

        with open(config_path, 'r') as file:
            for line in file:
                # strip trailing spaces
                line = line.strip()

                # only channelCfg, chirpComnCfg and frameCfg are of interest
                if line.startswith("ChannelCfg"):
                    parts = line.split()
                    vals = parts[1:]
                    num_rx_ant = bin(int(vals[0])).count('1')
                    num_tx_ant = bin(int(vals[1])).count('1')
                    
                elif line.startswith("chirpComnCfg"):
                    parts = line.split()
                    vals = parts[1:]
                    num_adc_samples = int(vals[3])
                    
                elif line.startswith("frameCfg"):
                    parts = line.split()
                    vals = parts[1:]
                    num_chirps_per_burst = int(vals[0])
                    num_bursts_per_frame = (vals[3])

        chirps_per_frame = num_chirps_per_burst * num_bursts_per_frame
        return chirps_per_frame, num_tx_ant, num_rx_ant, num_adc_samples
    
    @staticmethod
    def _decode_raw_data(raw):
        # TODO

    @staticmethod
    def _deswizzle(data):
        # TODO

    
    

    