import serial
import time
from tqdm import tqdm

class RadarCLI():
    """
    mmWave CLI adapter for sending commands to the mmWave CLI of the radar EVM.
    Usage:
        cli = RadarCLI('/dev/ttyACM1')
        cli.send_start_cmd()
        cli.send_config("/path/to/cfg")
        cli.close()
    """
    def __init__(self, radar_serial_port):
        try:
            self.ser = serial.Serial(radar_serial_port, baudrate=115200)
        except Exception as e:
            print(f"Unable to open serial port {radar_serial_port}: {e}")
            raise
    
    def _send_and_listen(self, command, keyword="Done", timeout=2, encoding='utf-8'):
        """
        Sends a command, listens for a keyword in the reply within an overall timeout.
        """
        if not self.ser or not self.ser.is_open:
            print("Error: Serial port not open.")
            return False

        try:
            # Send command
            self.ser.write((command + '\n').encode(encoding))

            # Listen for reply
            end_time = time.time() + timeout
            while time.time() < end_time:
                received_bytes = self.ser.readline()
                if received_bytes:
                    try:
                        line_str = received_bytes.decode(encoding)
                        if keyword in line_str:
                            return True
                    except UnicodeDecodeError:
                        return False
            
            return False # Keyword not found within timeout
        except serial.SerialException as e:
            print(f"Serial communication error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
    
    def send_config(self, config_path):
        """
        Sends supplied .cfg file liune by line to the radar mmWave CLI and checks for success by
        listening for "Done" as response.
        """
        
        with open(config_path, 'r') as file:
            for i, line in enumerate(tqdm(file)):
                # Remove leading/trailing whitespace (includes \r, \n, spaces, tabs)
                line = line.strip()
                # Ignore comments and empty lines
                if not line or line.startswith('%'):
                    continue

                # Write and check for success
                bytes_to_send = (line + '\n').encode('utf-8')
                success = self._send_and_listen(bytes_to_send)
                if not success:
                    raise Exception("Failed to send config to radar")

    def send_start_cmd(self):
        """Sends RF frontend start command."""
        self._send_and_listen("sensorStart 0 0 0 0")

    def send_stop_cmd(self):
        """Sends RF frontend stop command."""
        self._send_and_listen("sensorStop 0")

    def close(self):
        """Sends RF frontend stop command and closes the serial connection."""
        self._send_and_listen("sensorStop 0")
        if self.ser.is_open:
            self.ser.close()

