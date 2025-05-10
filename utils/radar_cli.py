"""
Module for interacting with a Texas Instruments mmWave radar EVM via its Command Line Interface
(mmWave CLI). Only works when TI's mmWave OOB Demo (or Motion and Presence Detection Demo) is 
running as it implements the mmWave CLI.

This module provides the `RadarCLI` class, which enables sending configuration commands and
starting and stopping the radar sensor.

The class handles:
- Opening and closing the serial connection to the radar's CLI port.
- Sending commands and checking for expected acknowledgment ("Done")
- Sending a full configuration file (e.g., a standard .cfg file from mmWave SDK)
  line by line
- Sending commands to start and stop the radar sensor.

Typical Usage:
    from radar_cli import RadarCLI
    try:
        cli = RadarCLI(radar_serial_port=RADAR_SERIAL_PORT)
        cli.send_config(config_path=CONFIG_FILE_PATH)
        print("Successfully sent config to radar")

        if cli.send_start_cmd():
            print("Successfully sent start command to radar")
        
        # ...

        if cli.send_stop_cmd():
            print("Successfully sent stop command to radar")
        
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    except FileNotFoundError as e:
        print(f"Configuration file error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cli:
            cli.close()
    
"""
import serial
from serial import SerialException
import time
from tqdm import tqdm

class RadarCLI():
    """
    mmWave CLI adapter for sending commands to the mmWave CLI of the radar EVM.
    Usage:
        cli = RadarCLI('/dev/ttyACM1')
        cli.send_config("/path/to/cfg")
        cli.send_start_cmd()
        ...
        cli.send_stop_cmd()
        cli.close()
    """
    def __init__(self, radar_serial_port):
        """
        Initializes the RadarCLI.

        Args:
            radar_serial_port (str): The serial port for radar communication (e.g., "/dev/ttyACM1", "COM3").
        """
        try:
            self.ser = serial.Serial(radar_serial_port, baudrate=115200, timeout=1)
        except Exception as e:
            print(f"Unable to open serial port {radar_serial_port}: {e}")
            raise
    
    def _send_and_listen(self, command, keyword="Done", timeout=2, encoding='utf-8'):
        """
        Sends a command, listens for a keyword in the reply within a timeout.

        Args:
            command (str): The command string to send (without newline).
            keyword (str): The keyword to look for in the radar's response.
            timeout (float): Total time in seconds to wait for the keyword.
            encoding (str): The encoding to use for sending and receiving data.

        Returns:
            bool: True if the keyword was found in the response, False otherwise.

        Raises:
            serial.SerialException: If the serial port is not open or a communication error occurs.
        """
        
        if not self.ser or not self.ser.is_open:
            raise SerialException("Serial port not open or available.")

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
        except SerialException as e:
            print(f"Serial communication error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
    
    def send_config(self, config_path):
        """
        Sends supplied .cfg file line by line to the radar mmWave CLI.

        Args:
            config_path (str): Path to the radar configuration file.

        Raises:
            FileNotFoundError: If the config file is not found.
            Exception: If any command from the config file fails to send or be acknowledged.
        """
        
        with open(config_path, 'r') as file:
            for i, line in enumerate(tqdm(file)):
                # Remove leading/trailing whitespace (includes \r, \n, spaces, tabs)
                line = line.strip()
                # Ignore comments and empty lines
                if not line or line.startswith('%'):
                    continue

                # Write and check for success
                success = self._send_and_listen(line)
                if not success:
                    raise Exception("Failed to send config to radar")

    def send_start_cmd(self):
        """Sends RF frontend start command."""
        return self._send_and_listen("sensorStart 0 0 0 0")

    def send_stop_cmd(self):
        """Sends RF frontend stop command."""
        return self._send_and_listen("sensorStop 0")

    def close(self):
        """Sends RF frontend stop command and closes the serial connection."""
        if self.ser and self.ser.is_open:
            self._send_and_listen("sensorStop 0")
            self.ser.close()
            self.ser = None

