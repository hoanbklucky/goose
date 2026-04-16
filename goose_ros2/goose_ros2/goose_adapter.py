# goose_adapter.py

class GooseAdapter:
    def __init__(self):
        """
        Initialize your Goose model/pipeline here
        Example:
            load neural network
            initialize preprocessing
        """
        pass

    def process(self, frame):
        """
        Input: OpenCV frame
        Output:
            offset (float)
            angle (float)  [optional]
        """

        # === STUDENTS REPLACE THIS ===
        # Example placeholder:
        h, w, _ = frame.shape
        offset = 0.0
        angle = 0.0

        return offset, angle