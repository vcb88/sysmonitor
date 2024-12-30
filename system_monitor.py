import psutil
import time
import os
import docker
import socket
from datetime import datetime
from collections import deque

class SystemMonitor:
    def __init__(self, history_length=60):
        self.docker_client = docker.from_env()
        self.history_length = history_length
        # Initialize histories for graphs
        self.cpu_history = deque(maxlen=history_length)
        self.memory_history = deque(maxlen=history_length)
        self.disk_usage_history = deque(maxlen=history_length)
        self.docker_containers_history = deque(maxlen=history_length)
        
    def get_cpu_usage(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_history.append(cpu_percent)
        return cpu_percent
    
    def get_memory_usage(self):
        memory = psutil.virtual_memory()
        self.memory_history.append(memory.percent)
        return memory.percent
    
    def get_disk_space(self):
        disk = psutil.disk_usage('/')
        self.disk_usage_history.append(disk.percent)
        return {
            'total': disk.total / (1024**3),  # GB
            'free': disk.free / (1024**3),    # GB
            'percent': disk.percent
        }
    
    def get_docker_space(self):
        try:
            info = self.docker_client.df()
            total_space = sum(image['Size'] for image in info['Images'])
            volumes_space = sum(volume['UsageData']['Size'] for volume in info['Volumes'] if volume['UsageData'])
            containers_space = sum(container['SizeRw'] for container in info['Containers'] if container.get('SizeRw'))
            
            total_used = (total_space + volumes_space + containers_space) / (1024**3)  # Convert to GB
            return total_used
        except Exception as e:
            return f"Docker space error: {str(e)}"
    
    def get_docker_containers(self):
        try:
            containers = self.docker_client.containers.list()
            count = len(containers)
            self.docker_containers_history.append(count)
            return {
                'count': count,
                'names': [container.name for container in containers]
            }
        except Exception as e:
            self.docker_containers_history.append(0)
            return {'count': 0, 'names': [f"Docker containers error: {str(e)}"]}
    
    def get_used_ports(self):
        used_ports = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN':
                used_ports.append(f"{conn.laddr.ip}:{conn.laddr.port}")
        return sorted(used_ports)
    
    def create_bar(self, percent, width=30):
        filled = int(width * percent / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f'[{bar}] {percent:.1f}%'
    
    def create_sparkline(self, data, width=30):
        if not data:
            return "░" * width
        
        # Normalize data for the graph
        min_val = min(data)
        max_val = max(data)
        if min_val == max_val:
            normalized = [4 for _ in data]  # Middle line
        else:
            normalized = [int(7 * (x - min_val) / (max_val - min_val)) for x in data]
        
        # Characters for different graph levels
        spark_chars = "▁▂▃▄▅▆▇█"
        
        # Create graph
        graph = ''.join(spark_chars[n] for n in normalized[-width:])
        return graph
    
    def display_metrics(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"\n{'=' * 60}")
        print(f"System Monitor - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'=' * 60}\n")
        
        # CPU
        cpu_percent = self.get_cpu_usage()
        print(f"CPU Usage:")
        print(f"{self.create_bar(cpu_percent)}")
        print(f"Last minute trend:")
        print(f"{self.create_sparkline(self.cpu_history)}\n")
        
        # Memory
        mem_percent = self.get_memory_usage()
        print(f"Memory:")
        print(f"{self.create_bar(mem_percent)}")
        print(f"Last minute trend:")
        print(f"{self.create_sparkline(self.memory_history)}\n")
        
        # Disk
        disk_info = self.get_disk_space()
        print(f"Disk:")
        print(f"Free: {disk_info['free']:.1f}GB of {disk_info['total']:.1f}GB")
        print(f"{self.create_bar(disk_info['percent'])}")
        print(f"Usage trend:")
        print(f"{self.create_sparkline(self.disk_usage_history)}\n")
        
        # Docker space
        docker_space = self.get_docker_space()
        print(f"Docker Storage:")
        if isinstance(docker_space, float):
            print(f"Used: {docker_space:.1f}GB\n")
        else:
            print(f"{docker_space}\n")
        
        # Docker containers
        containers = self.get_docker_containers()
        print(f"Docker Containers ({containers['count']}):")
        print(f"Container count trend:")
        print(f"{self.create_sparkline(self.docker_containers_history)}")
        for name in containers['names']:
            print(f"- {name}")
        print()
        
        # Network ports
        ports = self.get_used_ports()
        print(f"Used Network Ports ({len(ports)}):")
        for port in ports:
            print(f"- {port}")

def main():
    monitor = SystemMonitor()
    try:
        while True:
            monitor.display_metrics()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
