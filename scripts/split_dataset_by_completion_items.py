import os
import sys
import json
import argparse
from loguru import logger

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--completion_item_corpus", type=str)
    parser.add_argument(
        "--repo_root",
        type=str,
        default="/Users/tannpopo/coding/coding-interfere/repo_to_mine",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/Users/tannpopo/Projects/coder-ask-for-help/data_collection/data/completion_items",
    )
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    comp_file_name = args.completion_item_corpus.split("/")[-1].split(".")[0]

    with open(args.completion_item_corpus, "r") as f:
        completion_items = json.load(f)

        repo_set = set()
        for file_path, reqs in completion_items.items():
            relative_file_path = file_path[len(args.repo_root) + 1 :]
            repo_name = relative_file_path.split("/")[0]
            repo_set.add(repo_name)
        repo_set = list(repo_set)

        import random

        random.seed(16)
        valid_repo_set = random.sample(repo_set, int(len(repo_set) * 0.1))
        train_repo_set = [x for x in repo_set if x not in valid_repo_set]

        print(valid_repo_set)

        idx = 0
        valid_comp_items = {}
        train_comp_items = {}
        valid_cnt = 0
        train_cnt = 0
        for file_path, reqs in completion_items.items():
            relative_file_path = file_path[len(args.repo_root) + 1 :]
            repo_name = relative_file_path.split("/")[0]

            for req in reqs:
                req["id"] = idx
                req["repo"] = repo_name
                req["file"] = relative_file_path
                idx += 1
                if repo_name in valid_repo_set:
                    valid_cnt += 1
                else:
                    train_cnt += 1

            if repo_name in valid_repo_set:
                valid_comp_items[file_path] = reqs
            else:
                train_comp_items[file_path] = reqs

        with open(f"{args.output_dir}/{comp_file_name}_valid.json", "w") as f:
            logger.info(f"Valid: {valid_cnt}")
            json.dump(valid_comp_items, f, indent=4)
        with open(f"{args.output_dir}/{comp_file_name}_train.json", "w") as f:
            logger.info(f"Train: {train_cnt}")
            json.dump(train_comp_items, f, indent=4)
