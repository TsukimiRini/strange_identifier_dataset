import re


def index_to_coordinates(s, index):
    """Returns (line_number, col) of `index` in `s`."""
    if not len(s):
        return 1, 1
    sp = s[: index + 1].splitlines(keepends=True)
    return len(sp), len(sp[-1])


def coordinates_to_index(s, line, col):
    """Returns the index of the character at (line, col) in `s`."""
    return sum(len(line) for line in s.splitlines(keepends=True)[: line - 1]) + col - 1


def find_first_identifier(s, index):
    """Returns the first identifier after `index` in `s`."""
    pattern = r"[a-zA-Z_][a-zA-Z0-9_]*"
    match = re.search(pattern, s[index:])
    if match is None:
        return None
    return match.group(0)


if __name__ == "__main__":
    dataset_path = "monitors4codegen/datasets/DotPrompts/dataset.csv"
    project_dir = "/Users/tannpopo/Projects/coder-ask-for-help/data_collection"
    repos_dir = f"{project_dir}/data/dot_prompt_repos"
    output_path = f"{project_dir}/data/dot_prompt_instances.json"

    import sys
    import os
    from loguru import logger

    sys.path.append(
        "/Users/tannpopo/Projects/coder-ask-for-help/data_collection/monitors4codegen/src"
    )
    from monitors4codegen.multilspy import SyncLanguageServer
    from monitors4codegen.multilspy.multilspy_config import MultilspyConfig
    from monitors4codegen.multilspy.multilspy_logger import MultilspyLogger
    from tqdm import tqdm
    import json
    import logging
    from csv import DictReader

    config = MultilspyConfig.from_dict(
        {"code_language": "java"}
    )  # Also supports "python", "rust", "csharp"
    _logger = MultilspyLogger()
    logging.basicConfig(filename="multispy.log")

    with open(dataset_path) as f:
        dataset = list(DictReader(f))

    repo_to_insts = {}

    for inst in dataset:
        repo = inst["repo"]
        if repo not in repo_to_insts:
            repo_to_insts[repo] = []
        repo_to_insts[repo].append(inst)

    validation_datasets = []

    def buildForRepo(repo, dot_list):
        repo_path = os.path.join(repos_dir, repo.split("/")[1])
        if not os.path.exists(repo_path):
            return None
        logger.info(f"Start {repo_path}")
        # lsp = SyncLanguageServer.create(config, _logger, repo_path)
        # with lsp.start_server():
        #     for dot in tqdm(dot_list):
        #         file_name = dot["classFileName"]
        #         method_start = int(dot["methodStartIdx"])
        #         method_end = int(dot["methodStopIdx"])
        #         dot_idx = int(dot["dot_idx"])
        #         file_path = f"{repo_path}/{file_name}"
        #         with open(file_path, 'r') as f:
        #             file_content = f.read()
        #         line, col = index_to_coordinates(file_content, dot_idx)
        #         completion_items = lsp.request_completions(file_path, line-1, col)
        #         gt_identifier = find_first_identifier(file_content, dot_idx+1)
        #         if completion_items is None or completion_items == []:
        #             print(f"failed for file {file_name}, {dot_idx}, {line}, {col}, {gt_identifier}")
        #             completion_items = []
        #         dot["completion_items"] = completion_items
        #         dot["next_identifier"] = gt_identifier
        #         dot["method_completion"] = file_content[dot_idx+1:method_end]
        #         dot["line"] = line
        #         dot["col"] = col
        #         with open(output_path, "a") as f:
        #             f.write(json.dumps(dot))
        #             f.write("\n")

        for dot in tqdm(dot_list):
            file_name = dot["classFileName"]
            method_start = int(dot["methodStartIdx"])
            method_end = int(dot["methodStopIdx"])
            dot_idx = int(dot["dot_idx"])
            file_path = f"{repo_path}/{file_name}"
            with open(file_path, "r") as f:
                file_content = f.read()
            line, col = index_to_coordinates(file_content, dot_idx)
            gt_identifier = find_first_identifier(file_content, dot_idx + 1)

            dot["context"] = file_content[: dot_idx + 1]
            dot["next_identifier"] = gt_identifier
            dot["method_completion"] = file_content[dot_idx + 1 : method_end] + "}"
            dot["line"] = line
            dot["col"] = col
            # with open(output_path, "a") as f:
            #     f.write(json.dumps(dot))
            #     f.write("\n")

        logger.info(f"Finished {repo}")
        return dot_list

    with open(output_path, "w") as f:
        pass

    flag = True
    for repo in repo_to_insts.keys():
        result_of_repo = buildForRepo(repo, repo_to_insts[repo])
        if result_of_repo is not None:
            validation_datasets.extend(result_of_repo)
        else:
            print(f"failed for {repo}")

    with open(output_path, "w") as f:
        json.dump(validation_datasets, f, indent=4)
