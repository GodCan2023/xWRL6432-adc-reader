
import time
import threading
from queue import Queue
from queue import Empty as QueueEmpty

class ADCRecorder(threading.Thread):
    """
    A thread-based class to record a specified number of data frames
    from an input queue.

    It consumes frames from the queue, stores them, and stops once the 
    target number of frames is reached or when explicitly stopped.
    """
    def __init__(self, input_queue: Queue, num_frames: int):
        """
        Initializes the ADCRecorder.

        Args:
            input_queue: The queue from which frames are read. 
            num_frames (int): The total number of frames to record.

        Raises:
            ValueError: If num_frames is negative.
        """
        super().__init__(daemon=True)

        if not isinstance(num_frames, int) or num_frames < 0:
            raise ValueError("num_frames must be a non-negative integer.")

        self.input_queue = input_queue
        self.num_frames_to_record = num_frames
        
        self.recorded_frames = []
        self._frames_recorded_count = 0
        self._running = False
        
        # Event to signal completion of the recording task (all frames done or stopped)
        self.recording_task_complete_event = threading.Event()

    def run(self):
        """
        Continuously reads frames from the input_queue until the desired number
        of frames is recorded or the recording is stopped via the _running flag.
        """
        try:
            while self._running and self._frames_recorded_count < self.num_frames_to_record:
                try:
                    # Read frame from input_queue with a timeout of 1s and add to recorded_frames[]
                    frame = self.input_queue.get(timeout=1.0)
                    self.recorded_frames.append(frame)
                    self._frames_recorded_count += 1
                except QueueEmpty:
                    print("Timeout: Input Queue was empty for one second.")
                    raise
            
            if self._frames_recorded_count == self.num_frames_to_record:
                print(f"ADC Recorder: Successfully recorded all {self.num_frames_to_record} targeted frames.")
            elif not self._running: # Stopped by stop_recording()
                print(f"ADC Recorder: Recording stopped externally. Recorded {self._frames_recorded_count} of {self.num_frames_to_record} targeted frames.")

        except Exception as e:
            print(f"ADC Recorder: An error occurred during recording: {e}")
        finally:
            self._running = False
            # Set event that indicates that recording has completed
            self.recording_task_complete_event.set()

    def start_recording(self) -> bool:
        """
        Starts the recording process.

        Returns:
            bool: True if the recording thread was started successfully.
        """
        if self._running:
            print("ADC Recorder: Cannot start. Recording thread is already active.")
            return False
        
        self.recorded_frames = []
        self._frames_recorded_count = 0
        self.recording_task_complete_event.clear()
        
        self._running = True
        
        try:
            super().start()
            return True
        except RuntimeError as e:
            self._running = False
            self.recording_task_complete_event.set()
            print(f"ADC Recorder: Failed to start recording thread (RuntimeError: {e}). Has it been started before?")
            return False

    def stop_recording(self, wait_for_thread_join: bool = True, timeout: float = 2.0):
        """
        Signals the recording thread to stop its operation and optionally waits for it to join.

        Args:
            wait_for_thread_join (bool): If True, this method will block until the
                                         recording thread finishes or the timeout is reached.
            timeout (float): Maximum time in seconds to wait for the thread to join if
                             wait_for_thread_join is True.
        """
        print("ADC Recorder: Attempting to stop recording...")
        self._running = False

        if wait_for_thread_join and self.is_alive():
            self.join(timeout) 
            if self.is_alive():
                print("ADC Recorder: Recording thread did not terminate within the specified timeout via join().")
            else:
                print("ADC Recorder: Recording thread joined successfully.")

    def get_recorded_frames(self) -> list:
        """
        Returns the list of frames that have been recorded.

        Returns:
            list: A list containing the recorded frames.
        """
        if self._running and not self.recording_task_complete_event.is_set():
            print("ADC Recorder: Warning - Requesting data while recording is actively in progress.")
        return self.recorded_frames

    def get_frames_recorded_count(self) -> int:
        """
        Returns the number of frames that have been successfully recorded.
        """
        return self._frames_recorded_count

    def is_active(self) -> bool:
        """
        Checks if the recording thread is currently alive and its _running flag is set.
        This indicates an active attempt to record.
        """
        return self.is_alive() and self._running

    def wait_for_completion(self, timeout: float = None) -> bool:
        """
        Blocks the calling thread until the recording task is marked as complete

        Args:
            timeout (float, optional): Maximum time in seconds to wait for the
                                       completion event. If None, waits indefinitely.
        Returns:
            bool: True if the recording task completed (event was set) within the timeout,
                  False if the timeout occurred before the event was set.
        """
        if not self.is_alive() and self.recording_task_complete_event.is_set():
            return True # Already completed
        return self.recording_task_complete_event.wait(timeout)
