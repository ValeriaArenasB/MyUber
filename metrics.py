# NO ESTA IMPLEMENTADO
import json
import threading
import time

class Metrics:
    def __init__(self, metrics_file="metrics.json"):
        self.metrics = {
            "response_times": [],  # To calculate min, max, avg
            "successful_services": 0,
            "failed_services": 0,
            "timed_out_requests": 0
        }
        self.lock = threading.Lock()  # For thread-safe updates
        self.metrics_file = metrics_file

    def log_response_time(self, response_time):
        with self.lock:
            self.metrics["response_times"].append(response_time)

    def increment_successful_services(self):
        with self.lock:
            self.metrics["successful_services"] += 1

    def increment_failed_services(self):
        with self.lock:
            self.metrics["failed_services"] += 1

    def increment_timed_out_requests(self):
        with self.lock:
            self.metrics["timed_out_requests"] += 1

    def get_aggregated_metrics(self):
        with self.lock:
            response_times = self.metrics["response_times"]
            if response_times:
                min_time = min(response_times)
                max_time = max(response_times)
                avg_time = sum(response_times) / len(response_times)
            else:
                min_time = max_time = avg_time = 0

            return {
                "min_response_time": min_time,
                "max_response_time": max_time,
                "avg_response_time": avg_time,
                "successful_services": self.metrics["successful_services"],
                "failed_services": self.metrics["failed_services"],
                "timed_out_requests": self.metrics["timed_out_requests"]
            }

    def save_metrics(self):
        with self.lock:
            aggregated_metrics = self.get_aggregated_metrics()
            with open(self.metrics_file, "w") as file:
                json.dump(aggregated_metrics, file, indent=4)
            print(f"Metrics saved to {self.metrics_file}")
