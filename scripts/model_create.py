import argparse
import logging
import sys
import os
import pathlib
import shutil
import subprocess
import yaml

from model.SOC_Model import SOCModel 
from model.SOH_Model import SOHModel 

CONFIG_YAML="config.yaml"

# add model create argument parser
def add_create_parser(subparsers, _):
    """Include parser for 'create' subcommand"""
    parser = subparsers.add_parser("create", help="create ml model")
    parser.set_defaults(func=model_create)
    parser.add_argument("--workspace", help="specify workspace path", required=True)
    parser.add_argument("--model_type", help="specify model scenario soc/soh", default='soc', required=True)
    parser.add_argument("--dataset_folder", help="specify dataset folder", required=True)
    parser.add_argument("--train_file", help="specify training dataset(csv) file", required=True)
    parser.add_argument("--test_file", help="specify test dataset(csv) file", required=True)
    parser.add_argument("--epochs", help="specify training epochs", type=int, default=100)

#project generate main function
def model_create(args):
    print(f"model type is {args.model_type}")
    model_type = args.model_type
    workspace_path = args.workspace
    train_dataset = args.train_file
    test_dataset = args.test_file
    dataset_path = args.dataset_folder
    epochs = args.epochs

    if model_type == 'soc':
        model_file, test_data_file = SOCModel(workspace_path, dataset_path, train_dataset, test_dataset, epochs)
    else:
        model_file, test_data_file = SOHModel(workspace_path, dataset_path, train_dataset, test_dataset, epochs)

    if os.path.exists(CONFIG_YAML):
        os.remove(CONFIG_YAML)

    if model_file and test_data_file:
        conf_data = {
            'workspace': workspace_path,
            'model_type': model_type,
            'model_file': model_file,
            'model_test_data_file': test_data_file 
        }

        with open(CONFIG_YAML, 'w') as file:
            # default_flow_style=False keeps the human-readable block format
            yaml.dump(conf_data, file, default_flow_style=False)
    return model_file
