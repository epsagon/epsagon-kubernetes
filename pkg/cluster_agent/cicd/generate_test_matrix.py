"""
Generates the system test file paths & cluster config file matrix.
This is written to save time during CI/CD and support custom cluster config.
"""
import os
import sys
import json

TEST_PATH_MODE = "test-path"
CLUSTER_CONFIG_MODE = "cluster-config-file"
USAGE = (
    f"Usage: python generate_test_matrix"
    " <{TEST_FILE_MODE}|{CLUSTER_CONFIG_MODE}>"
)
CLUSTER_CONFIG_FILENAME = "cluster_config.yml"
SYSTEM_TEST_DIRPATH= "tests/system/"
DEFAULT_CLUSTER_CONFIG = os.path.join(SYSTEM_TEST_DIRPATH, CLUSTER_CONFIG_FILENAME)

def main(mode):
    test_path_mode = mode == TEST_PATH_MODE
    dirs = [result[0] for result in os.walk(SYSTEM_TEST_DIRPATH)]
    dirs.remove(SYSTEM_TEST_DIRPATH)
    if test_path_mode:
        print(json.dumps(dirs))
        return

    cluster_configs = [
        os.path.join(directory, CLUSTER_CONFIG_FILENAME)
        if os.path.exists(os.path.join(directory, CLUSTER_CONFIG_FILENAME))
        else DEFAULT_CLUSTER_CONFIG
        for directory in dirs
    ]
    print(json.dumps(cluster_configs))


if __name__ == '__main__':
    if len(sys.argv) != 2 :
        print(USAGE)
        sys.exit(1)
    mode = sys.argv[1]
    if mode not in (TEST_PATH_MODE, CLUSTER_CONFIG_MODE):
        print(USAGE)
        sys.exit(1)

    main(mode)


