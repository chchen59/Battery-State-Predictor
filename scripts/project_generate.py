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
    #board name, MCU
    ['NuMaker-M55M1', 'M55M1'],   
    ['NuGestureAI-M55M1', 'M55M1'],   
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


