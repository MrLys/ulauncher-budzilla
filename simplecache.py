import os
import time
import pickle

class SimpleCache:
    def __init__(self, filename, duration=60):
        self.filename = filename
        self.duration = duration

    def save(self, data):
        timestamp = time.time()
        with open(self.filename, 'wb') as f:
            pickle.dump((timestamp, data), f)

    def load(self):
        if not os.path.exists(self.filename):
            return None

        with open(self.filename, 'rb') as f:
            timestamp, data = pickle.load(f)

        # Check if the cache has expired
        if time.time() - timestamp > self.duration:
            self.clear()
            return None

        return data

    def clear(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

