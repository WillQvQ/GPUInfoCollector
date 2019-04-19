import os
import re
import json
import sys
import time

try:
    import urllib2 as urllib
    
    version = 2
except ImportError:
    import urllib.request as urllib
    
    version = 3

err_codes = {
    1001: "Can't get ip",
    1002: "Can't find gpus",
    1003: "Can't gpu info",
}


def get_ip():
    result = os.popen("ifconfig | grep addr:10")
    ips = result.read().strip().split()
    for each in ips:
        if each[:5] == "addr:":
            return 0, each[5:]
    return 0, "0.0.0.0"


def get_devices():
    result = os.popen("nvidia-smi -L")
    lines = result.readlines()
    devices = []
    for i, line in enumerate(lines):
        if line[:3] == 'GPU':
            uuid = re.findall(r"\(UUID: [\w-]+\)", line)[0][7:-1]
            name = re.findall(r"GPU \d:[\w ]+\(", line)[0][7:-2]
            devices.append({
                "id": i,
                "name": name,
                "uuid": uuid
            })
        else:
            return 1002, []
    return 0, devices


def get_line(line):
    line = re.findall(r"<[\w]+>[\w% ]+</[\w]+>", line)
    if line:
        line = line[0]
        name = line.split('>')[0][1:]
        value = line.split('>')[1].split('<')[0]
        return name, value
    else:
        return "", ""


def get_info_by_id(_id):
    result = os.popen("nvidia-smi --_id=" + str(_id) + " -q --xml-format")
    lines = result.readlines()
    need = {"gpu_util", "memory_util", "encoder_util", "decoder_util", "gpu_temp",
            "gpu_temp_max_threshold", "gpu_temp_slow_threshold", "fan_speed"}
    info = {}
    for line in lines:
        name, value = get_line(line)
        if name in need:
            info[name] = value.split()[0]
        if name == 'pid':
            pid = value
            grep = os.popen("grep \"Uid\" /proc/" + pid + "/status").readlines()
            uid = grep[0].split("\t")[1]
            username = os.popen("getent passwd " + uid).readlines()[0].split(":")[0]
            info["username"] = username
    return info


def get_info():
    err, ip = get_ip()
    if err:
        return err, {"err_code": err}
    err, devices = get_devices()
    if err:
        return err, {"err_code": err}
    for i, _ in enumerate(devices):
        info = get_info_by_id(i)
        for name in info:
            devices[i][name] = info[name]
            devices[i]["ip"] = ip
    return 0, devices


def send_info():
    err, data = get_info()
    data = json.dumps(data)
    if version == 3:
        data = bytes(data, 'utf8')
    try:
        if err:
            headers = {'Content-Type': 'application/json'}
            request = urllib.Request(url=err_report_url, headers=headers, data=data)
            _ = urllib.urlopen(request)
            print("send err info.", err)
        else:
            headers = {'Content-Type': 'application/json'}
            request = urllib.Request(url=report_url, headers=headers, data=data)
            _ = urllib.urlopen(request)
            print("send info.")
    except urllib.URLError:
        print("fail to send")


def keep_sending():
    print("Keep sending info to", base_url)
    while 1:
        send_info()
        time.sleep(time_interval)


if __name__ == "__main__":
    base_url = sys.argv[1]
    report_url = "http://" + base_url + "/post"
    err_report_url = "http://" + base_url + "/err"
    time_interval = 180
    keep_sending()
