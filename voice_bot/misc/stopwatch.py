import time


class Stopwatch:
    def __init__(self):
        self._time = time.perf_counter()

    def start(self) -> None:
        self._time = time.perf_counter()

    def stop(self) -> float:
        return time.perf_counter() - self._time
