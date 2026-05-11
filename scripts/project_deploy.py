import argparse
import sys
import os

from model_create import model_create
from project_generate import project_generate
from project_build import project_build
from project_flash import project_flash

def add_deploy_parser(subparsers, _):
    """Include parser for 'deploy' subcommand"""
    parser = subparsers.add_parser("deploy", help="deploy ml project")
    parser.set_defaults(func=project_deploy)
    parser.add_argument("--workspace", help="specify workspace path", required=True)
    parser.add_argument("--model_type", help="specify model scenario soc/soh", default='soc', required=True)
    parser.add_argument("--dataset_folder", help="specify dataset folder", required=True)
    parser.add_argument("--train_file", nargs="+", help="specify training dataset(csv) file", required=True)
    parser.add_argument("--test_file", help="specify test dataset(csv) file", required=True)
    parser.add_argument("--epochs", help="specify training epochs", type=int, default=100)
    parser.add_argument("--board", help="specify target board name", default='NuMaker-X-M55M1D')
    parser.add_argument("--model_arena_size", help="specify the size of arena cache memory in bytes", default='0')
    parser.add_argument("--vela_extra_option", help="specify vela extra options")
    parser.add_argument("--uv4_tool", help="specify UV4.exe path")
    parser.add_argument("--binary_file", help="specify project binary file")

def project_deploy(args):
    model_file = model_create(args)
    if model_file == None:
        return
    
    print(model_file)

    project_path = project_generate(args)
    if project_path == None:
        return

    print(project_path)

    project_bin_fiile = project_build(args)

    if project_bin_fiile == None:
        return

    print(project_bin_fiile)

    project_flash(args)
