import time
import daemon
import lockfile
import re
from contextlib import closing
import pymysql
from pymysql.cursors import DictCursor
from daemon import pidfile
import json

prev_total = {}
prev_idle = {}
total = {}
idle = {}
usage = {}
memory = {}
disk = {}

def calc_cpu():
    with open('/proc/stat') as cpu_stats:
        for line in cpu_stats:
            result = re.match(r'cpu(\d)?', line)
            if result:
                stats = re.split(r'\s+', line)
                total[result.group(0)] = int(stats[1]) + int(stats[2]) + int(stats[3]) + int(stats[4]) + int(stats[5]) + int(stats[7])
                idle[result.group(0)] = int(stats[4])
                diff_total = total[result.group(0)] - (prev_total[result.group(0)] if prev_total.get(result.group(0)) else 0)
                diff_idle = idle[result.group(0)] - (prev_idle[result.group(0)] if prev_idle.get(result.group(0)) else 0)
                usage[result.group(0)] = (1000*(diff_total-diff_idle)/diff_total+5)/10
                prev_total[result.group(0)] = total[result.group(0)]
                prev_idle[result.group(0)] = idle[result.group(0)]
        cpu_stats.close()
    # print(usage)

def calc_ram():
    with open('/proc/meminfo') as memory_stats:
        for line in memory_stats:
            name = re.search(r'MemTotal|MemFree|Buffers|^Cached', line)
            if name:
                kbytes = re.search(r'\d+', line)
                memory[name.group(0)] = kbytes.group(0)
        memory_stats.close()
    # print(memory)

def calc_io():
    with open('/proc/diskstats') as disk_stats:
        for line in disk_stats:
            name = re.search(r'sd[a-z]\d*', line)
            if name:
                stats = re.findall(r'sd[a-z]\d*\s+(\d+.*)*', line)
                disk[name.group(0)] = re.split(r'\s+', stats[0])
        disk_stats.close()
    # print(disk)

def daemon_program():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='password',
        db='some_tables',
        charset='utf8',
        cursorclass=DictCursor
    )
    while True:
        calc_cpu()
        calc_ram()
        calc_io()
        with connection.cursor() as cursor:
            query = 'INSERT INTO comp_stats(cpu, ram, io) VALUES(\'' + json.dumps(usage) + '\', \'' + json.dumps(memory) + '\', \'' + json.dumps(disk) + '\')'
            cursor.execute(query)
            connection.commit()
        # for cpu_name in usage:
        #     print(cpu_name + ": " + str(usage[cpu_name]) + "%")
        # print("\r", end=" ")
        # print(str(usage['cpu']) + "%\r", end="")
        # print(memory)
        time.sleep(1)

daemon_program()

# with daemon.DaemonContext(working_directory="/home/wgpavell/python-monitor-daemon/", pidfile=pidfile.TimeoutPIDLockFile("/var/run/monitor.pid")):
#     daemon_program()
