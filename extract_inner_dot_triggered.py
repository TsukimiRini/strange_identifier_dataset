import os
import sys
import json
sys.path.append("/Users/tannpopo/Projects/coder-ask-for-help/data_collection/monitors4codegen/src")
from monitors4codegen.multilspy import SyncLanguageServer
from monitors4codegen.multilspy.multilspy_config import MultilspyConfig
from monitors4codegen.multilspy.multilspy_logger import MultilspyLogger
from tqdm import tqdm

config = MultilspyConfig.from_dict({"code_language": "java"}) # Also supports "python", "rust", "csharp"
_logger = MultilspyLogger()

forget_gap = 9999
repo_root = "/Users/tannpopo/coding/coding-interfere/repo_to_mine/"
completion_items_file = f"datasets/strange_identifiers_{forget_gap}_completion_items.json"
inner_completion_items_file = f"datasets/strange_identifiers_{forget_gap}_inner_labeled_completion_items.json"

with open(completion_items_file, 'r') as f:
    completion_items = json.load(f)

repo_to_files = {}
for file_path, reqs in tqdm(completion_items.items()):
    # if file_path in valid_file_set:
    #     output_file = valid_file
    # else:
    #     output_file = train_file
    relative_file_path = file_path[len(repo_root):]
    repo_name = relative_file_path.split("/")[0]
    relative_file = relative_file_path[len(repo_name)+1:]
    repo_path = os.path.join(repo_root, repo_name)
    repo_to_files[repo_name] = repo_to_files.get(repo_name, []) + [(file_path, reqs)]

for repo_name, inst in tqdm(repo_to_files.items()):
    repo_path = os.path.join(repo_root, repo_name)
    lsp = SyncLanguageServer.create(config, _logger, repo_path)
    with lsp.start_server():
        for file_path, reqs in inst:
            relative_file_path = file_path[len(repo_root):]
            relative_file = relative_file_path[len(repo_name)+1:]
            for req in reqs:
                trigger_point = req["trigger_point"]
                try:
                    definition = lsp.request_definition(relative_file, int(trigger_point[0]), int(trigger_point[1])+1)
                except:
                    print(f"failed for file {relative_file}, {trigger_point[0]}, {trigger_point[1]}")
                    continue
                if len(definition) == 0:
                    req["lib"] = "unknown"
                elif definition[0]["absolutePath"].endswith(".class"):
                    req["lib"] = "true"
                else:
                    req["lib"] = "false"
                with open(inner_completion_items_file+".jsonl", 'a') as f:
                    f.write(json.dumps(req)+"\n")

with open(inner_completion_items_file, 'w') as f:
    json.dump(completion_items, f, indent=4)