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
import threading
import queue

class SerialMonitor(threading.Thread):
    """Thread for monitoring serial port data in real-time."""
    def __init__(self, serial_port, data_callback=None):
        super().__init__()
        self.serial_port = serial_port  # 使用传入的串口实例
        self.running = True
        self.daemon = True  # Make thread daemon so it exits when main program exits
        self.data_callback = data_callback  # 回调函数，用于通知接收到的数据
        
    def run(self):
        try:
            print(f"Started monitoring serial port")
            while self.running:
                if self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        # print(f"Serial Data: {data}")
                        # 如果设置了回调函数，则调用它
                        if self.data_callback:
                            self.data_callback(data)
                time.sleep(0.01)
        except Exception as e:
            print(f"Serial monitor error: {e}")
                
    def stop(self):
        self.running = False

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
            self.last_received_data = None  # 存储最后接收到的数据
            
            # Start serial monitor thread using the same serial port instance
            self.serial_monitor = SerialMonitor(self.ser, self.data_callback)
            self.serial_monitor.start()
        except Exception as e:
            print(f"Unable to open serial port {radar_serial_port}: {e}")
            raise
    
    def data_callback(self, data):
        """数据回调函数，用于更新最后接收到的数据"""
        self.last_received_data = data
    def get_last_received_data(self):
        """获取最后接收到的数据"""
        return self.last_received_data
    
    def _send_and_listen(self, command, timeout=2, encoding='utf-8') -> bool:
        """
        Sends a command, listens for "Done" in the reply within a timeout.

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
            # Clear the last received data before sending command
            self.last_received_data = None
            
            # Send command
            self.ser.write((command + '\n').encode(encoding))
            time.sleep(0.2)

            # Wait for response by checking last_received_data
            end_time = time.time() + timeout
            while time.time() < end_time:
                if self.last_received_data:
                    if "Done" in self.last_received_data:
                        return True
                    if "Error" in self.last_received_data:
                        print(f"Error response: {self.last_received_data}")
                        break
                time.sleep(0.1)  # Check every 100ms
            
            # Done keyword not found within timeout
            print(f"Could not get confirmation for command: {command}")
            return False
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
        print("Sending Config to radar EVM...")
        
        # Count lines in file
        with open(config_path, 'r') as f:
            total_lines = sum(1 for _ in f)
            if total_lines == 0:
                print("Config file is empty.")
                return

        with open(config_path, 'r') as file:
            with tqdm(total=total_lines, unit='line', desc="Sending Cfg", leave=True) as pbar:
                for i, line in enumerate(file):
                    # Remove leading/trailing whitespace (includes \r, \n, spaces, tabs)
                    line = line.strip()
                    # Ignore comments and empty lines
                    if not line or line.startswith('%'):
                        pbar.update(1)
                        continue

                    # Write and check for success
                    success = self._send_and_listen(line)
                    if not success:
                        raise Exception("Failed to send config to radar")
                    pbar.update(1)
        print("Config sent successfully.")

    def send_start_cmd(self) -> bool:
        """Sends RF frontend start command."""
        return self._send_and_listen("sensorStart 0 0 0 0")

    def send_stop_cmd(self) -> bool:
        """Sends RF frontend stop command."""
        return self._send_and_listen("sensorStop 0")

    def close(self):
        """Sends RF frontend stop command and closes the serial connection."""
        # First stop the monitor thread
        if hasattr(self, 'serial_monitor'):
            self.serial_monitor.stop()
            self.serial_monitor.join(timeout=1.0)  # Wait for thread to finish with timeout
        
        # Then close the main serial connection
        if self.ser and self.ser.is_open:
            self._send_and_listen("sensorStop 0")
            self.ser.close()
            self.ser = None