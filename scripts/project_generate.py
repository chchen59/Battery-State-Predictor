import argparse
import logging
import sys
import os
import pathlib
import shutil
import subprocess
import yaml

CONFIG_YAML="config.yaml"

PROJECT_GEN_DIR_PREFIX = 'ProjGen_'

board_list = [
    #board name, MCU, BSP name
    ['NuMaker-M55M1', 'M55M1', 'M55M1BSP-3.01.004'],   
    ['NuGestureAI-M55M1', 'M55M1', 'M55M1BSP-3.01.004'],   
]

application = {
    "soc"   : {
                    "board": ['NuMaker-M55M1', 'NuGestureAI-M55M1'],
                    "example_tmpl_dir": "soc_template",
                    "example_tmpl_proj": "BatterySOCEstimation"
                  },
    "soh"  : {
                    "board": ['NuMaker-M55M1', 'NuGestureAI-M55M1'],
                    "example_tmpl_dir": "soh_template",
                    "example_tmpl_proj": "BatterySOHEstimation"
                  },
}

def load_config(file_path):
    with open(file_path, 'r') as stream:
        try:
            # safe_load converts YAML into a Python dictionary
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

# INT8 model compile by vela
def model_compile(board_info, output_path, vela_dir_path, model_file, model_arena_size, extra_option):
    cur_work_dir = os.getcwd()
    os.chdir(output_path)
    vela_exe = os.path.join(vela_dir_path, 'vela-4_0_1.exe')    
    vela_conf_file = os.path.join(vela_dir_path, 'default_vela.ini')
    vela_conifg_option = '--config='+vela_conf_file
    print(output_path)
    print(vela_conifg_option)
    print(model_file)
    print(model_arena_size)
    print(vela_exe)

    vela_cmd = [vela_exe, model_file, '--accelerator-config=ethos-u55-256', '--optimise=Performance', vela_conifg_option, '--memory-mode=Shared_Sram', '--system-config=Ethos_U55_High_End_Embedded', '--output-dir=.']

    if int(model_arena_size) > 0:
        vela_cmd.extend(['--arena-cache-size', model_arena_size])

    if extra_option != None:
        print(extra_option)
        extra_option_parts = extra_option.split()
        vela_cmd.extend(extra_option_parts)

    print(vela_cmd)
    ret =subprocess.run(vela_cmd)
    if ret.returncode == 0:
        print('vela compile done')
    else:
        print('Unable compile failee')
        return False

    os.chdir(cur_work_dir)
    return True

#generate tflite cpp file
def generate_model_cpp(output_path, tflite2cpp_dir_path, model_file):
    cur_work_dir = os.getcwd()
    print(cur_work_dir)
    os.chdir(output_path)
    model2cpp_exe = os.path.join(tflite2cpp_dir_path, 'gen_model_cpp.exe')
    template_dir = os.path.join(tflite2cpp_dir_path, 'templates')
    model2cpp_cmd = [model2cpp_exe, '--tflite_path', model_file, '--output_dir','.', '--template_dir', template_dir, '-ns', 'arm', '-ns', 'app', '-ns', 'nn']   
    print(model2cpp_cmd)

    ret =subprocess.run(model2cpp_cmd)
    if ret.returncode == 0:
        print('tflite2cpp done')
    else:
        print('Unable generate cpp')
        return False

    os.chdir(cur_work_dir)
    return True

# add project generate argument parser
def add_generate_parser(subparsers, _):
    """Include parser for 'generate' subcommand"""
    parser = subparsers.add_parser("generate", help="generate ml project")
    parser.set_defaults(func=project_generate)
    parser.add_argument("--board", help="specify target board name", default='NuMaker-M55M1')
    parser.add_argument("--model_arena_size", help="specify the size of arena cache memory in bytes", default='0')
    parser.add_argument("--vela_extra_option", help="specify vela extra options")


#project generate main function
def project_generate(args):
    #check config.yaml
    if os.path.exists(CONFIG_YAML) == False:
        print("The config.yaml didn't exist. Please run create command first")
        return

    #load config.yaml
    conf = load_config(CONFIG_YAML)

    application_usage = conf['model_type']
    workspace_dir = conf['workspace']
    model_file = conf['model_file']

    if not application_usage in application:
        print("applicaiton not found!")
        return

    application_param = application[application_usage]
    templates_path = os.path.join(os.path.dirname(__file__), 'templates')

    board_found = False

    for board_info in board_list:
        if board_info[0] == args.board:
            for supported_board in application_param["board"]:
                if supported_board == args.board:
                    board_found = True
                    break
        if board_found == True:
            break

    if board_found == False:
        print("board not support")
        return

    #generated project directory
    project_path = os.path.join(workspace_dir, PROJECT_GEN_DIR_PREFIX + args.board)
    if not os.path.exists(project_path):
        os.mkdir(project_path)

    #model compile by vela
    arena_size = args.model_arena_size
    vela_dir_path = os.path.join(os.path.dirname(__file__), '..', 'vela')

    ret = model_compile(board_info, workspace_dir, vela_dir_path, os.path.abspath(model_file), arena_size, args.vela_extra_option)
    if ret == False:
        return

    vela_model_basename = os.path.splitext(os.path.basename(model_file))[0]
    vela_model_file_path = os.path.join(workspace_dir, vela_model_basename + '_vela.tflite')
    vela_summary_file_path = os.path.join(workspace_dir, vela_model_basename + '_summary_Ethos_U55_High_End_Embedded.csv')
    print(vela_model_file_path)

    #generate model cc file
    tflite2cpp_dir_path = os.path.join(os.path.dirname(__file__), '..', 'tflite2cpp')
    print(tflite2cpp_dir_path)
    generate_model_cpp(workspace_dir, tflite2cpp_dir_path, os.path.abspath(vela_model_file_path)) 
    vela_model_cc_file = os.path.join(workspace_dir, vela_model_basename + '_vela.tflite.cc')
    print(vela_model_cc_file)
