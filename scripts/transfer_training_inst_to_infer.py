import json
import os
import sys
import argparse
from dot_prompt_transfer import find_first_identifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--insts", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--type", type=str, choices=["lib", "inner", "mixed"])
    parser.add_argument("--cnt", type=int)
    args = parser.parse_args()

    def load_training_data(file_path):
        with open(file_path, "r") as f:
            training_instances = [json.loads(x) for x in f.readlines()]
        return training_instances

    def trim_tags(str):
        if "<request>" in str:
            str = "".join(str.split("<request>")[:-1])
        if "</request>" in str:
            str = "".join(str.split("</request>")[1:])
        return str

    data = load_training_data(args.insts)
    results = []
    for idx, inst in enumerate(data):
        if "generation" not in inst["type"]:
            continue
        context = trim_tags(inst["context"])
        completion = trim_tags(inst["completion"])
        results.append(
            {
                "repo": inst["repo"],
                "classFileName": inst["file"],
                "methodStartIdx": None,
                "methodStopIdx": None,
                "dot_idx": len(context) - 1,
                "context": context,
                "next_identifier": find_first_identifier(
                    context + completion, len(context)
                ),
                "method_completion": completion,
                "line": None,
                "col": None,
                "id": idx,
                "lib": inst["lib"],
            }
        )

    if args.type == "lib":
        results = [x for x in results if x["lib"] == "true"]
        print(len(results))
    elif args.type == "inner":
        results = [x for x in results if x["lib"] == "false"]
        print(len(results))
    elif args.type == "mixed":
        results = results
        print(len(results))

    import random

    random.seed(16)
    results = random.sample(results, args.cnt)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=4)
