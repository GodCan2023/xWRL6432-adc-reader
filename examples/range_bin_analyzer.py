import numpy as np
import matplotlib.pyplot as plt
import mplcursors
class RangeBinAnalyzer:
    """
    Python implementation of MATLAB rangeBin function.
    
    This class analyzes range bin data to find the bin with maximum energy
    after removing static components.
    """
    
    def __init__(self):
        """Initialize the RangeBinAnalyzer."""
        pass
    
    def range_bin(self, map_data, display_or_not=False):
        """
        Find the range bin with maximum energy after static removal.
        
        Args:
            map_data (numpy.ndarray): 2D array where each row represents data for a range bin
            display_or_not (bool): Whether to display the result plot
        
        Returns:
            int: Index of the range bin with maximum energy (0-based indexing)
        """
        # Convert to numpy array if not already
        map_data = np.array(map_data)
        
        # Calculate mean for each row (axis=0 means along columns for each row)
        row_means = np.mean(map_data, axis=0, keepdims=True)
        
        # Calculate energy: sum of absolute differences from mean for each row
        y = np.sum((map_data - row_means)**2, axis=0);
        
        # Find maximum values and their indices for each row
        max_values = np.max(y, axis=1)  # Get maximum values
        index = np.argmax(y, axis=1)    # Get indices of maximum values
        # 删除能量值小于阈值的索引
        valid_indices = max_values >= 5e7
        index = index[valid_indices]  # 只保留能量值大于阈值的索引
        # 如果index为空,给其赋值为0
        if len(index) == 0:
            index = np.array([0])  # 为3个接收通道都赋值为0
        
        if display_or_not:
            self._display_energy_plot(y, index)
        
        return  int(round(np.mean(index)))

    
    def _display_energy_plot(self, y, max_index):
        """
        Display the energy plot similar to MATLAB version.
        
        Args:
            y (numpy.ndarray): Energy values for each range bin
            max_index (int): Index of the maximum energy bin
        """
        # Convert to dB scale
        # y_db = 10 * np.log10(y / np.max(y))
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(y[0,:], linewidth=2, label='RX1')
        plt.plot(y[1,:], linewidth=2, label='RX2')
        plt.plot(y[2,:], linewidth=2, label='RX3')
        
        # Highlight the maximum point
        # Plot maximum points for each channel
        plt.plot(max_index[0], y[0,max_index[0]], 'ro', markersize=8, label=f'RX1 Max at {max_index[0]}')
        plt.plot(max_index[1], y[1,max_index[1]], 'go', markersize=8, label=f'RX2 Max at {max_index[1]}')
        plt.plot(max_index[2], y[2,max_index[2]], 'yo', markersize=8, label=f'RX3 Max at {max_index[2]}')
        
        plt.title('Energy with static removing', fontsize=16)
        plt.xlabel('Range Bin Index', fontsize=16)
        plt.ylabel('dB', fontsize=16)
        # mplcursors.cursor(hover=True)
        plt.grid(True)
        plt.legend()
        
        # Set font size for axes
        plt.tick_params(labelsize=14)
        
        # Optional: set y-axis limits similar to MATLAB commented code
        # plt.ylim([-10, 0])
        
        plt.tight_layout()
        plt.show()