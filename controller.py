import os, sys


def get_ip():
    result = os.popen("ifconfig | grep addr:10")
    ips = result.read().strip().split()
    for each in ips:
        if each[:5] == "addr:":
            return 0, each[5:]
    return 0, "0.0.0.0"


def update_with_screen(lines=None):
    if lines is None:
        with open("servers.csv", "r")as fin:
            lines = fin.readlines()
    for each in lines[1:]:
        data = each.split(",")
        with open("run.sh", "w") as fout:
            fout.write(
                f"""#!/usr/bin/expect
                
                set host {data[0]}
                set user {data[1]}
                set timeout 2
                
                spawn ssh $user@$host
                expect "*password:*"
                send "{data[2]}\r"
                expect "*]#"
                send "screen -S nvidia_reporter -X quit\r"
                expect "*]#"
                send "rm -rf .nvidia_reporter{data[0][-3:]}/\r"
                expect "*]#"
                send "mkdir .nvidia_reporter\r"
                expect "*]#"
                send "cd .nvidia_reporter\r"
                expect "*]#"
                send "wget http://{base_url}/reporter\r"
                expect "*]#"
                send "mv reporter reporter.py\r"
                expect "*]#"
                send "screen -S nvidia_reporter\r"
                expect "*]#"
                send "python reporter.py {base_url}\r"
                expect "*]#"
                send "exit\r"
                expect eof""")
        os.system("chmod 777 run.sh && ./run.sh")
        print(f"\n====={data[0]}, ok!=====\n")
    os.system("rm run.sh")


def stop_screen():
    with open("servers.csv", "r")as fin:
        lines = fin.readlines()
    for each in lines[1:]:
        data = each.strip('\n').split(",")
        with open("run.sh", "w") as fout:
            fout.write(
                f"""#!/usr/bin/expect
                
                set host {data[0]}
                set user {data[1]}
                set timeout 2
                
                spawn ssh $user@$host
                expect "*password:*"
                send "{data[2]}\r"
                expect "*]#"
                send "screen -S nvidia_reporter -X quit\r"
                expect "*]#"
                send "rm -rf .nvidia_reporter{data[0][-3:]}/\r"
                expect "*]#"
                send "exit\r"
                expect eof""")
        os.system("chmod 777 run.sh && ./run.sh")
        print(f"\n====={data[0]}, ok!=====\n")
    os.system("rm run.sh")


def create_users():
    shell_context = """#!/bin/sh

echo \\\"Remove old account if exist\\\"
userdel -r -f \\\"\\$1\\\" || true
echo \\\"Add new account for \\$1\\\"
useradd -m \\$1 -d /remote-home/\\$1 -u \\$2 -U
echo \\\"Change password for \\$1\\\"
echo \\\"\\$1\\n\\$1\\\" | passwd \\\"\\$1\\\"
mkdir /remote-home/\\$1
chown \\$1:\\$1 /remote-home/\\$1
echo \\\"Add \\$1 to group sudo\\\"
chsh \\$1 -s /bin/bash

echo \\\"DONE\\\" """
    with open("users.csv", "r")as fin:
        lines = fin.readlines()
    commands = ""
    for line in lines[1:]:
        if line.startswith("#"):
            continue
        line = line.strip('\n').split(',')
        commands += f"""send "sudo bash ./add_remote.sh {line[0]} {line[1]}\n" \nexpect "*]#"\n"""
    with open("servers.csv", "r")as fin:
        lines = fin.readlines()
    for each in lines[1:]:
        data = each.strip('\n').split(",")
        with open("run.sh", "w") as fout:
            fout.write(
                f"""#!/usr/bin/expect
                
                set host {data[0]}
                set user {data[1]}
                set timeout 2
                
                spawn ssh $user@$host
                expect "*password:*"
                send "{data[2]}\r"
                expect "*]#"
                send "sudo su\r"
                expect "*password:*"
                send "{data[2]}\r"
                expect "*]#"
                send "echo -e '"""
                + shell_context +
                """ '> add_remote.sh\r"
                expect "*]#"\n"""
                + commands +
                """send "rm add_remote.sh\r"
                expect "*]#"
                send "exit\r"
                expect eof""")
        os.system("chmod 700 run.sh && ./run.sh")
        print(f"\n====={data[0]}, ok!=====\n")
    os.system("rm run.sh")


if __name__ == "__main__":
    err, ip = get_ip()
    if err > 0:
        print("Can't get the IP address.")
    else:
        base_url = ip + ':8997'
        if len(sys.argv) == 1:
            print("-u Update all reporters (with servers.csv)")
            print("-s Stop all reporters (with servers.csv)")
            print("-c Create remote-home for users (with users.csv)")
        elif sys.argv[1] == '-u':
            update_with_screen()
        elif sys.argv[1] == '-s':
            stop_screen()
        elif sys.argv[1] == '-c':
            create_users()
