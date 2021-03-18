"""
Gets the cluster config file path according to given testing directory path.
If the config is not found then using the default cluster configuration.
"""
import os
import sys
import json

USAGE = (
    f"Usage: python get_test_cluster_config.py <test_directory>"
)
CLUSTER_CONFIG_FILENAME = "cluster_config.yml"
SYSTEM_TEST_DIRPATH= "tests/system/"
DEFAULT_CLUSTER_CONFIG = os.path.join(SYSTEM_TEST_DIRPATH, CLUSTER_CONFIG_FILENAME)

def main(test_directory):
    cluster_config_path = DEFAULT_CLUSTER_CONFIG
    file_path = os.path.join(directory, CLUSTER_CONFIG_FILENAME)
    if os.path.exists(file_path):
        cluster_config_path = file_path

    print(json.dumps(cluster_config_path))


if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        print(USAGE)
        sys.exit(1)

    main(args[1])


