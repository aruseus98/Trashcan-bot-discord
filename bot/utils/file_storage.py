import json
import os

CONF_DIR = "conf"
FILE_PATH = os.path.join(CONF_DIR, "deletion_tasks.json")

if not os.path.exists(CONF_DIR):
    os.makedirs(CONF_DIR)

def save_tasks(tasks):
    with open(FILE_PATH, 'w') as file:
        json.dump(tasks, file, default=str, indent=4)

def load_tasks():
    if not os.path.exists(FILE_PATH):
        return []
    with open(FILE_PATH, 'r') as file:
        tasks = json.load(file)
    return tasks
