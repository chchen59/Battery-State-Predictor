import os
import shutil
import subprocess
import yaml
import winreg

CONFIG_YAML="config.yaml"

def load_config(file_path):
    with open(file_path, 'r') as stream:
        try:
            # safe_load converts YAML into a Python dictionary
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

def read_registry_value(hive, subkey, value_name):
    """
    Reads a value from the Windows Registry.

    Args:
        hive: The root key of the registry (e.g., winreg.HKEY_LOCAL_MACHINE).
        subkey: The path to the subkey (e.g., "SOFTWARE\\Microsoft\\Windows\\CurrentVersion").
        value_name: The name of the value to read (e.g., "ProgramFilesDir").

    Returns:
        The data of the specified value, or None if an error occurs.
    """
    try:
        # Open the specified registry key
        key_handle = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)

        # Query the value data
        value_data, value_type = winreg.QueryValueEx(key_handle, value_name)

        # Close the key handle
        winreg.CloseKey(key_handle)

        return value_data

    except FileNotFoundError:
        print(f"Error: Registry key '{subkey}' or value '{value_name}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def uvision5_build(uv4_util, proj_file_dir, proj_name):
    print('start building ...')
    cur_work_dir = os.getcwd()
    os.chdir(proj_file_dir)
    build_cmd = [uv4_util, '-b', proj_name + '.uvprojx']
    subprocess.run(build_cmd)
    print('build done')
    os.chdir(cur_work_dir)

    binary_file = os.path.join(proj_file_dir, 'build', proj_name + '.bin')
    if os.path.exists(binary_file): 
        return binary_file
    else:
        return None

def add_build_parser(subparsers, _):
    """Include parser for 'build' subcommand"""
    parser = subparsers.add_parser("build", help="build ml project")
    parser.set_defaults(func=project_build)
    parser.add_argument("--uv4_tool", help="specify UV4.exe path")

def project_build(args):
    #check config.yaml
    if os.path.exists(CONFIG_YAML) == False:
        print("The config.yaml didn't exist. Please run create command first!")
        return

    #load config.yaml
    conf = load_config(CONFIG_YAML)

    if not 'project_path' in conf:
        print(" The project_path setting is not in config.yaml. Please run generate command first!")
        return

    project_path = conf['project_path']
    project_dir = os.path.join(project_path, 'Keil')
    project_name = os.path.basename(project_path)

    print('checking build tool ...')
    uv4_util = args.uv4_tool

    if uv4_util == None:
        if os.name == 'nt':
            hive = winreg.HKEY_LOCAL_MACHINE
            subkey = "SOFTWARE\\WOW6432Node\\Keil\\Products\\MDK"
            value_name = "Path"
            Keil_path = read_registry_value(hive, subkey, value_name)

            if Keil_path != None:
                uv4_util = os.path.dirname(Keil_path)
                uv4_util = os.path.join(uv4_util, 'UV4', 'UV4.exe')

    if uv4_util == None:
        uv4_util = shutil.which('UV4.exe')

    if uv4_util == None or not os.path.isfile(uv4_util):
        print('UV4.exe not found, you must specify correct UV4.exe path!')
        return

    binary_file = uvision5_build(uv4_util, project_dir, project_name)

    if binary_file == None:
        print('Build project failed!')
        return

    conf.update({"project_binary_file":binary_file})

    with open(CONFIG_YAML, 'w') as file:
        # default_flow_style=False keeps the human-readable block format
        yaml.dump(conf, file, default_flow_style=False)

    return binary_file
