import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import sys

# Add the parent directory to path to import the range_bin_analyzer
sys.path.append(str(Path(__file__).resolve().parent.parent))
from range_bin_analyzer import RangeBinAnalyzer

# NPZ_FILE_PATH = Path("logs/frame_dump_20250620_181433.npz")
NPZ_FILE_PATH = Path("examples/last_frame.npz")
# Read chirp parameters from metadata or set manually

BANDWIDTH = 6.4 * 1e9
if not NPZ_FILE_PATH.is_file():
    raise FileNotFoundError(f"Error: The specified NPZ file was not found at: {NPZ_FILE_PATH}")
try:
    loaded_data = np.load(NPZ_FILE_PATH, allow_pickle=True)
except Exception as e:
    print(f"Error loading NPZ file: {e}")

available_keys = list(loaded_data.keys())

if 'config_metadata' in loaded_data:
    try:
        config_metadata = loaded_data['config_metadata'].item()
        if isinstance(config_metadata, dict):
            print("Successfully extracted 'config_metadata' dictionary")
        else:
            print(f"Warning: 'config_metadata' key exists but is not a dictionary. Type: {type(config_metadata)}")
            config_metadata = None
    except Exception as e:
        print(f"Error extracting 'config_metadata'. It might not be stored correctly. Error: {e}")
else:
    print("Warning: 'config_metadata' key not found in the NPZ file.")



num_chirps_per_frame = config_metadata.get("num_chirps_per_frame")
num_tx_ant = config_metadata.get("num_tx_ant")
num_rx_ant = config_metadata.get("num_rx_ant")
num_adc_samples = config_metadata.get("num_adc_samples")
num_chirp_loops = config_metadata.get("num_chirp_loops")

print(f"Extracted Parameters:")
print(f"  num_chirps_per_frame: {num_chirps_per_frame}")
print(f"  num_tx_ant: {num_tx_ant}")
print(f"  num_rx_ant: {num_rx_ant}")
print(f"  num_adc_samples: {num_adc_samples}")
print(f"  num_chirp_loops: {num_chirp_loops}")

essential_params = [num_chirps_per_frame, num_tx_ant, num_rx_ant, num_adc_samples, num_chirp_loops]
if None in essential_params:
    print("\nWarning: One or more essential configuration parameters were not found in the metadata dictionary.")


adc_data_frames = None

if 'adc_data' in loaded_data:
    adc_data_frames = loaded_data['adc_data']
    print(f"Successfully loaded 'adc_data'.")
    print(f"  Shape: {adc_data_frames.shape}") # Expected: (num_frames, num_chirp_loops, num_channels, num_adc_samples)
    print(f"  Data Type: {adc_data_frames.dtype}")
else:
    print("Error: 'adc_data' key not found in the NPZ file. Cannot load frame data.")


# Read other saved information (e.g., frame counts)
print("\n--- Reading Other Saved Information ---")
recorded_frame_count = None
target_frame_count = None

if 'num_frames_recorded_actual' in loaded_data:
    # Saved as np.array(int), so use .item() to get the scalar back
    recorded_frame_count = loaded_data['num_frames_recorded_actual'].item()
    print(f"Actual number of frames recorded: {recorded_frame_count}")

if 'num_frames_target_config' in loaded_data:
    # Saved as np.array(int), so use .item() to get the scalar back
    target_frame_count = loaded_data['num_frames_target_config'].item()
    print(f"Target number of frames configured: {target_frame_count}")

# --- Configuration: Select which chirp/channel to plot ---
frame_index_to_plot = 1024       # Index of the frame to use
chirp_loop_index_to_plot = 0  # Index of the chirp loop within the frame
channel_index_to_plot = 2    # Index of the virtual channel (0 to num_tx_ant * num_rx_ant - 1)
# --- End Configuration ---
num_virtual_antennas = num_tx_ant * num_rx_ant

num_frames_loaded = adc_data_frames.shape[0]
num_chirp_loops_loaded = adc_data_frames.shape[1]
num_channels_loaded = adc_data_frames.shape[2]
num_samples_loaded = adc_data_frames.shape[3]
print(f"Info: num_frames_loaded: {num_frames_loaded}, num_chirp_loops_loaded: {num_chirp_loops_loaded}, num_channels_loaded: {num_channels_loaded}, num_samples_loaded: {num_samples_loaded}")

print(f"Selected data: Frame {frame_index_to_plot}, Chirp Loop {chirp_loop_index_to_plot}, Channel {channel_index_to_plot}")

# Extract the chirp of interest from the frame
selected_chirp = adc_data_frames[0:frame_index_to_plot, chirp_loop_index_to_plot, 0:3, :]
print(f"  Extracted chirp data shape: {selected_chirp.shape}")

# Apply a Hanning window to reduce FFT sidelobes
# selected_chirp shape: (1024, 256), window shape: (256,)
# Need to broadcast window to match selected_chirp dimensions
window = np.hanning(num_adc_samples)  # Shape: (256,)
chirp_windowed = selected_chirp * window  # Shape: (1024, 256)

# FFT along the ADC samples dimension
range_fft_complex = np.fft.fft(chirp_windowed, n=num_adc_samples, axis=2)

# Calculate Magnitude (often plotted in dB, but linear magnitude first)
# We only need the first half of the FFT result due to symmetry for real inputs
range_fft_magnitude = np.abs(range_fft_complex[:,:,:num_adc_samples // 2])

# Use RangeBinAnalyzer to find the range bin with maximum energy
print("\n=== Range Bin Analysis ===")
analyzer = RangeBinAnalyzer()

# Call range_bin with display enabled
print(f"Input data shape: {range_fft_magnitude.shape}")
max_range_bin = analyzer.range_bin(range_fft_magnitude[:,:,:], display_or_not=True)



print(f"Range bin with maximum energy: {max_range_bin}")

# Convert to actual range if bandwidth is known
c = 3e8  # speed of light (m/s)
range_resolution = c / (2 * BANDWIDTH)
max_range_meters = max_range_bin * range_resolution
print(f"Estimated target range: {max_range_meters:.3f} meters")

# Plotting
# Create an array representing FFT bins (proportional to range)
range_bins = np.arange(num_adc_samples // 2)
fame_index = np.arange(frame_index_to_plot)

# Create meshgrid for 3D plotting
X, Y = np.meshgrid(range_bins, fame_index)

# # Calculate dB magnitude for the second plot
# epsilon = 1e-10
# range_fft_db = 20 * np.log10(range_fft_magnitude + epsilon)

fig = plt.figure(figsize=(16, 8))

# First subplot - Linear magnitude
ax = fig.add_subplot(121, projection='3d')
ax.plot_surface(X, Y, range_fft_magnitude[:,0,:], cmap='viridis', alpha=0.8)
# ax.plot_surface(X, Y, range_fft_magnitude[:,1,:], cmap='viridis', alpha=0.8)
# ax.plot_surface(X, Y, range_fft_magnitude[:,2,:], cmap='viridis', alpha=0.8)

ax.set_title(f'Range Profile (FFT Magnitude)\nFrame: {frame_index_to_plot}, Chirp Loop: {chirp_loop_index_to_plot}, Channel: {channel_index_to_plot}')
ax.set_xlabel('Range Bin Index')
ax.set_ylabel('Frame Index')
ax.set_zlabel('FFT Magnitude (Linear Scale)')

# Second subplot - Range profile with target detection
ax_db = fig.add_subplot(122)
ax_db.plot(range_bins, range_fft_magnitude[0,0,:], 'r-', linewidth=1, label='RX1')
ax_db.plot(range_bins, range_fft_magnitude[0,1,:], 'g-', linewidth=1, label='RX2')
ax_db.plot(range_bins, range_fft_magnitude[0,2,:], 'y-', linewidth=1, label='RX3')
ax_db.grid(True)  # Enable grid display
ax_db.legend()

ax_db.set_title(f'Range Profile with Target Detection\nFrame: 0, Chirp Loop: {chirp_loop_index_to_plot}, Channel: {channel_index_to_plot}')
ax_db.set_xlabel('Range Bin Index')
ax_db.set_ylabel('FFT Magnitude')

plt.tight_layout() # Adjust layout to prevent labels overlapping
plt.show()


# Extract phase data for the target range bin across all frames
target_range_bin_complex = range_fft_complex[:,:, max_range_bin]

# Calculate phase (in radians)
phase_raw = np.angle(target_range_bin_complex)
# Phase unwrapping
phase_unwrapped = np.unwrap(phase_raw,axis=0)


# Calculate phase difference (velocity information)
phase_diff = np.diff(phase_unwrapped,axis=0)
# Create phase analysis plots
fig, ((ax1, ax2)) = plt.subplots(1, 2, figsize=(15, 10))

# Plot 1: Raw phase
ax1.plot(phase_raw[:,0], 'r-', linewidth=1, alpha=0.7)


ax1.set_title(f'Raw Phase - Range Bin {max_range_bin}')
ax1.set_xlabel('Frame Index')
ax1.set_ylabel('Phase (degrees)')
ax1.grid(True, alpha=0.3)

# Plot 2: Unwrapped phase
ax2.plot(phase_unwrapped[:,0], 'r-', linewidth=1)


ax2.set_title(f'Unwrapped Phase - Range Bin {max_range_bin}')
ax2.set_xlabel('Frame Index')
ax2.set_ylabel('Unwrapped Phase (degrees)')
ax2.grid(True, alpha=0.3)


plt.tight_layout()
plt.show()

# === Vital Signs Analysis ===
print("\n=== Vital Signs Analysis ===")

# Import the VitalSignsAnalyzer
from vital_signs_analyzer import VitalSignsAnalyzer

# Create analyzer instance
vital_analyzer = VitalSignsAnalyzer()

# Use the phase data from the target range bin for vital signs analysis
print(f"Analyzing vital signs using phase data from range bin {max_range_bin}")
print(f"Phase data shape: {phase_raw.shape}")

# Call analyze_vital_signs with periodicity = 0.05
periodicity = 0.05
print(f"Using periodicity: {periodicity}")

# Perform vital signs analysis with display
BR, HR = vital_analyzer.display3s(phase_unwrapped, periodicity)

print(f"\nVital Signs Analysis Results:")
# Process breathing rate data - remove outliers
BR_filtered = BR.copy()
mb = np.abs(np.mean(BR_filtered) - BR_filtered)
while len(BR_filtered) > 1:
    max_idx = np.argmax(mb)
    max_val = mb[max_idx]
    if max_val < 1:
        break
    BR_filtered = np.delete(BR_filtered, max_idx)
    mb = np.abs(np.mean(BR_filtered) - BR_filtered)
avg_br = np.mean(BR_filtered)

# Process heart rate data - remove outliers
HR_filtered = HR.copy()
mb = np.abs(np.mean(HR_filtered) - HR_filtered)
while len(HR_filtered) > 1:
    max_idx = np.argmax(mb)
    max_val = mb[max_idx]
    if max_val < 1:
        break
    HR_filtered = np.delete(HR_filtered, max_idx)
    mb = np.abs(np.mean(HR_filtered) - HR_filtered)
avg_hr = np.mean(HR_filtered)

print(f"Average BR={avg_br:.2f} BPM HR={avg_hr:.2f} BPM")
