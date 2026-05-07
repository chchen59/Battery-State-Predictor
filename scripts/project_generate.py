import argparse
import logging
import sys
import os
import pathlib
import shutil
import subprocess
import yaml

from soc_codegen.soc_codegen import SOCCodegen
from soh_codegen.soh_codegen import SOHCodegen

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

def prepare_proj_resource(board_info, project_path, templates_path, vela_model_file, vela_model_cc_file, pattern_test_file, example_tmpl_dir, example_tmpl_proj):
    print('copy resources to autogen project directory')

    bsp_lib_src_path = os.path.join(templates_path, board_info[1], board_info[2], 'Library')
    bsp_lib_dest_path = os.path.join(project_path, board_info[2],'Library')
    print('copy bsp library to autogen project directory')
    shutil.copytree(bsp_lib_src_path, bsp_lib_dest_path, dirs_exist_ok = True)    

    bsp_thirdparty_src_path = os.path.join(templates_path, board_info[1], board_info[2], 'ThirdParty')
    bsp_thirdparty_dest_path = os.path.join(project_path, board_info[2], 'ThirdParty')

    bsp_thirdparty_tflite_micro_src_path = os.path.join(bsp_thirdparty_src_path, 'tflite_micro')
    bsp_thirdparty_tflite_micro_dest_path = os.path.join(bsp_thirdparty_dest_path, 'tflite_micro') 
    print('copy BSP ThirdParty tflite_micro ...')
    shutil.copytree(bsp_thirdparty_tflite_micro_src_path, bsp_thirdparty_tflite_micro_dest_path, dirs_exist_ok = True)

    bsp_thirdparty_fatfs_src_path = os.path.join(bsp_thirdparty_src_path, 'FatFs')
    bsp_thirdparty_fatfs_dest_path = os.path.join(bsp_thirdparty_dest_path, 'FatFs') 
    print('copy BSP ThirdParty FatFs ...')
    shutil.copytree(bsp_thirdparty_fatfs_src_path, bsp_thirdparty_fatfs_dest_path, dirs_exist_ok = True)

    bsp_thirdparty_openmv_src_path = os.path.join(bsp_thirdparty_src_path, 'openmv')
    bsp_thirdparty_openmv_dest_path = os.path.join(bsp_thirdparty_dest_path, 'openmv')
    print('copy BSP ThirdParty openmv ...')
    shutil.copytree(bsp_thirdparty_openmv_src_path, bsp_thirdparty_openmv_dest_path, dirs_exist_ok = True)

    bsp_thirdparty_ml_evk_src_path = os.path.join(bsp_thirdparty_src_path, 'ml-embedded-evaluation-kit')
    bsp_thirdparty_ml_evk_dest_path = os.path.join(bsp_thirdparty_dest_path, 'ml-embedded-evaluation-kit')
    print('copy BSP ThirdParty ml-embedded-evaluation-kit ...')
    shutil.copytree(bsp_thirdparty_ml_evk_src_path, bsp_thirdparty_ml_evk_dest_path, dirs_exist_ok = True)

    bsp_dest_path = os.path.join(project_path, board_info[2])
    example_template_path = os.path.join(templates_path, board_info[1], board_info[0], example_tmpl_dir)
    example_project_path = os.path.join(bsp_dest_path, 'SampleCode', 'MachineLearning')
    example_project_src_path = os.path.join(example_template_path, example_tmpl_proj)

    print(example_template_path)
    print(example_project_src_path)
    print(example_project_path)

    print('copy example template project to autogen MachineLearning example folder')
    example_project_path = os.path.join(example_project_path, example_tmpl_proj)
    shutil.copytree(example_project_src_path, example_project_path, dirs_exist_ok = True)

    print('copy example model file to autogen MachineLearning example folder')
    example_project_model_cpp_file = os.path.join(example_project_path, 'Model', 'NN_Model_INT8.tflite.cpp')
    example_project_model_dir = os.path.join(example_project_path, 'Model')
    shutil.copyfile(vela_model_cc_file, example_project_model_cpp_file)
    shutil.copy(vela_model_file, example_project_model_dir)

    print('copy example test pattern file to autogen MachineLearning example folder')
    example_project_pattern_dir = os.path.join(example_project_path, 'Pattern')
    shutil.copy(pattern_test_file, example_project_pattern_dir)

    return example_project_path

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
    pattern_test_file = conf['model_test_data_file']

    if not application_usage in application:
        print("applicaiton not found!")
        return

    if os.path.exists(model_file) == False:
        print("The model file didn't exist. Please run create command first")
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

    #prepare project resource
    example_tmpl_dir = application_param["example_tmpl_dir"]
    example_tmpl_proj = application_param["example_tmpl_proj"]

    project_example_path = prepare_proj_resource(board_info, project_path, templates_path, vela_model_file_path, vela_model_cc_file, pattern_test_file, example_tmpl_dir, example_tmpl_proj)
    print(project_example_path)

    # Generate model.hpp/cpp or main.cpp
    if application_usage == 'soc':
        codegen = SOCCodegen.from_args(vela_model_file_path, project_example_path, vela_summary_file_path, app='soc')
    elif application_usage == 'soh':
        codegen = SOHCodegen.from_args(vela_model_file_path, project_example_path, vela_summary_file_path, app='soh')

    codegen.code_gen()

    os.remove(vela_model_file_path)
    os.remove(vela_model_cc_file)

    conf.update({"target_board":board_info[0], "project_path":project_example_path})

    with open(CONFIG_YAML, 'w') as file:
        # default_flow_style=False keeps the human-readable block format
        yaml.dump(conf, file, default_flow_style=False)

    print(f'Example project completed at {os.path.abspath(project_example_path)}')
    return project_example_path