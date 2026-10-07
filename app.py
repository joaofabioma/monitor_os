from flask import Flask, render_template, jsonify
import psutil
import os
from datetime import datetime
import socket

app = Flask(__name__)

def get_disk_usage_details():
    """Obtém detalhes do uso de disco de forma organizada"""
    disk_info = []
    
    # Verifica todas as partições
    partitions = psutil.disk_partitions(all=False)
    
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            
            # Converte bytes para GB
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            free_gb = usage.free / (1024**3)
            percent = usage.percent
            
            disk_info.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'free_gb': round(free_gb, 2),
                'percent': percent,
                'opts': partition.opts
            })
        except (PermissionError, OSError):
            continue
    
    return disk_info

def get_large_directories(path="/", limit=20, max_depth=2):
    """Encontra os diretórios mais ocupados sem percorrer o sistema inteiro."""
    dir_sizes = []

    # Evita varrer o diretório raiz completo; em servidores isso costuma ser muito pesado
    # e pode exceder o timeout do Gunicorn. Limita a análise aos diretórios mais relevantes.
    search_roots = [path]
    if os.path.abspath(path) == "/":
        search_roots = [p for p in ["/var", "/home", "/opt", "/srv", "/usr", "/tmp", "/root"] if os.path.isdir(p)]
        if not search_roots:
            search_roots = [path]

    for base_path in search_roots:
        try:
            with os.scandir(base_path) as entries:
                items = [entry.path for entry in entries if entry.is_dir(follow_symlinks=False)]
        except (PermissionError, OSError):
            continue

        for item_path in items:
            try:
                total_size = 0

                for dirpath, dirnames, filenames in os.walk(item_path, topdown=True, followlinks=False):
                    current_depth = dirpath.count(os.sep) - item_path.count(os.sep)
                    if current_depth >= max_depth:
                        dirnames[:] = []

                    for filename in filenames:
                        try:
                            filepath = os.path.join(dirpath, filename)
                            total_size += os.path.getsize(filepath)
                        except (OSError, PermissionError):
                            continue

                dir_sizes.append({
                    'path': item_path,
                    'size_gb': round(total_size / (1024**3), 2)
                })
            except (PermissionError, OSError):
                continue

    dir_sizes.sort(key=lambda x: x['size_gb'], reverse=True)
    return dir_sizes[:limit]

def get_system_info():
    """Obtém informações do sistema"""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    # Memória
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Rede
    net_io = psutil.net_io_counters()
    
    # Sistema
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    return {
        'cpu': {
            'percent': cpu_percent,
            'cores': cpu_count,
            'freq_mhz': round(cpu_freq.current, 2) if cpu_freq else 'N/A'
        },
        'memory': {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'percent': memory.percent
        },
        'swap': {
            'total_gb': round(swap.total / (1024**3), 2),
            'used_gb': round(swap.used / (1024**3), 2),
            'percent': swap.percent
        },
        'network': {
            'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
            'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2)
        },
        'system': {
            'boot_time': boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            'uptime_days': uptime.days,
            'uptime_hours': uptime.seconds // 3600,
            'hostname': socket.gethostname()
        }
    }

@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    disk_info = get_disk_usage_details()
    system_info = get_system_info()
    
    # Analisa diretórios do principal mountpoint (geralmente /)
    main_mount = next((part for part in disk_info if part['mountpoint'] == '/'), None)
    large_dirs = get_large_directories("/", 10) if main_mount else []
    
    return render_template('dashboard.html',
                         disk_info=disk_info,
                         system_info=system_info,
                         large_dirs=large_dirs)

@app.route('/api/update')
def update_data():
    """API para atualização em tempo real (AJAX)"""
    disk_info = get_disk_usage_details()
    system_info = get_system_info()
    
    return jsonify({
        'disk': disk_info,
        'system': system_info,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5090, debug=True)
