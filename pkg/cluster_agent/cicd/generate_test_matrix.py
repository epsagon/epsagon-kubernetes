"""
Generates the system test file paths matrix.
This is written to save time during CI/CD and support custom cluster config.
"""
import os
import json

SYSTEM_TEST_DIRPATH= "tests/system/"

def main():
    dirs = [result[0] for result in os.walk(SYSTEM_TEST_DIRPATH)]
    dirs.remove(SYSTEM_TEST_DIRPATH)
    print(json.dumps(dirs))

if __name__ == '__main__':
    main()


