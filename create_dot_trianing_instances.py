import os
import json
import sys

sys.path.append("/Users/tannpopo/Projects/coder-ask-for-help/data_collection/monitors4codegen/src")
from monitors4codegen.multilspy import SyncLanguageServer
from monitors4codegen.multilspy.multilspy_config import MultilspyConfig
from monitors4codegen.multilspy.multilspy_logger import MultilspyLogger
from tqdm import tqdm
from loguru import logger
import logging

forget_gap = 9999
repos_dir = "/Users/tannpopo/coding/coding-interfere/repo_to_mine"
strange_identifiers_dir = f"/Users/tannpopo/coding/coding-interfere/strange_identifiers_{forget_gap}"
output_dir = f"/Users/tannpopo/coding/coding-interfere/strange_identifiers_{forget_gap}_completion_items"

os.makedirs(output_dir, exist_ok=True)
# execute a command "/usr/libexec/java_home" to get the JAVA_HOME
os.system("/usr/libexec/java_home")
# os.environ["JAVA_HOME"] = ""
# config = MultilspyConfig.from_dict({"code_language": "java"})

config = MultilspyConfig.from_dict({"code_language": "java"}) # Also supports "python", "rust", "csharp"
_logger = MultilspyLogger()
logging.basicConfig(filename="multispy.log")

def readInStrangeIdentifiers(repo):
    with open(f"{strange_identifiers_dir}/{repo}.json", "r") as f:
        strange_identifiers = json.load(f)
    return strange_identifiers

def buildForRepo(repo):
    repo_path = os.path.join(repos_dir, repo)
    logger.info(f"Start {repo_path}")
    strange_identifiers = readInStrangeIdentifiers(repo)
    lsp = SyncLanguageServer.create(config, _logger, repo_path)
    results = []
    with lsp.start_server():
        strange_identifier = strange_identifiers[0]
        for strange_identifier in tqdm(strange_identifiers):
            if "." not in strange_identifier["strange_identifier"]["full_name"]:
                continue
            start_col = strange_identifier["strange_identifier"]["start_col"]+len(strange_identifier["strange_identifier"]["full_name"])-len(strange_identifier["strange_identifier"]["name"])
            completion_items = lsp.request_completions(strange_identifier["file_path"][len(repo_path)+1:], strange_identifier["strange_identifier"]["start_row"], start_col)
            if completion_items is None or completion_items == []:
                print(f"failed for file {strange_identifier['file_path']}, {strange_identifier['strange_identifier']['start_row']}, {start_col}, {strange_identifier['strange_identifier']['full_name']}")
                continue
            strange_identifier["completion_items"] = []
            for completion_item in completion_items:
                strange_identifier["completion_items"].append(completion_item)
            results.append(strange_identifier)

        with open(f"{output_dir}/{repo}.json", "w") as f:
            json.dump(results, f, indent=4)

        logger.info(f"Finished {repo}, {len(results)}/{len(strange_identifiers)} completion items found")
        return results

# results = buildForRepo("daydayEXP")
    
lsp = SyncLanguageServer.create(config, _logger, "/Users/tannpopo/coding/coding-interfere/repo_to_mine/daydayEXP")
with lsp.start_server():
    completion_items = lsp.request_completions("src/main/java/com/bcvgh/controller/RemoteUpdatePOC.java", 82, 38)
    print(completion_items)