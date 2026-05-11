import os
import re
import shutil
import subprocess
import yaml

CONFIG_YAML="config.yaml"

board_list = [
    #board name, MCU, NuLinkTool
    ['NuMaker-M467HJ', 'M467', 'NuLink_M460_M2L31.exe'],
    ['NuMaker-X-M55M1D', 'M55M1', 'M55M1_M5531\\NuLink.exe'],
    ['NuGestureAI-M55M1', 'M55M1', 'M55M1_M5531\\NuLink.exe'],
]

def load_config(file_path):
    with open(file_path, 'r') as stream:
        try:
            # safe_load converts YAML into a Python dictionary
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

def add_flash_parser(subparsers, _):
    """Include parser for 'flash' subcommand"""
    parser = subparsers.add_parser("flash", help="flash binary code")
    parser.set_defaults(func=project_flash)
    parser.add_argument("--binary_file", help="specify project binary file")

def project_flash(args):

    #check config.yaml
    if os.path.exists(CONFIG_YAML) == False:
        print("The config.yaml didn't exist. Please run create command first!")
        return 1

    #load config.yaml
    conf = load_config(CONFIG_YAML)

    if args.binary_file != None:
        binary_file = args.binary_file
    else:
        if 'project_binary_file' in conf:
            binary_file = conf['project_binary_file']
    
    if binary_file == None:
        print(" The project_binary_file setting is not in config.yaml. Please run build command first!")
        return 2

    if not os.path.isfile(binary_file):
        print('The binary file not found')
        return

    binary_file_abspath = os.path.abspath(binary_file)
    board_found = False

    for board_info in board_list:
        if board_info[0] == conf['target_board']:
            board_found = True
            break

    if board_found == False:
        print("board not support")
        return 3

    #check nulink
    nulink_util = shutil.which(board_info[2])

    if nulink_util == None:
        nulink_util = os.path.join(os.path.dirname(__file__), '..', 'NuLink Command Tool', board_info[2])
        if not os.path.isfile(nulink_util):
            print('nulink not found')
            return 4

    print(f'NuLink tool: {nulink_util}')

    nulink_util_dir = os.path.dirname(nulink_util)
    cur_dir = os.getcwd()
    print(nulink_util_dir)
    os.chdir(nulink_util_dir)

    nulink_connect_cmd = [nulink_util, '-C']
    nulink_erase_cmd = [nulink_util, '-E', 'APROM']
    # Erase + Program APROM
    nulink_write_cmd = [nulink_util, '-W', 'APROM', binary_file_abspath, '1']
    nulink_reset_cmd = [nulink_util, '-S']

    print('connect target board')
    ret =subprocess.run(nulink_connect_cmd, shell=True)
    if ret.returncode == 0:
        print('connect MCU done')
    else:
        print('unable connect MCU')
        return 4

    """
    print('erase target')
    ret =subprocess.run(nulink_erase_cmd, shell=True, check=True)
    if ret.returncode == 0:
        print('erase MCU done')
    else:
        print('unable erase MCU')
        return 5
    """

    print(f'start program target MCU: {binary_file_abspath}')
    ret =subprocess.run(nulink_write_cmd, shell=True)
    if ret.returncode == 0:
        print('program MCU done')
    else:
        print('unable program MCU')
        return 6

    print('reset target')
    ret =subprocess.run(nulink_connect_cmd, shell=True)
    if ret.returncode == 0:
        print('connect MCU done')
    else:
        print('unable connect MCU')
        return 7

    ret =subprocess.run(nulink_reset_cmd, shell=True, check=True)
    if ret.returncode == 0:
        print('reset MCU done')
    else:
        print('reset erase MCU')
        return 8

    os.chdir(cur_dir)
    return 0
