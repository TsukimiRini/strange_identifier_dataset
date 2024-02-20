import json
import os
import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--training_instances_file", type=str)
    parser.add_argument("--output_path", type=str)
    parser.add_argument("--repo_root", type=str)
    parser.add_argument("--cnt", type=int, default=500)
    args = parser.parse_args()

    training_instances_file = args.training_instances_file
    robust_training_instances_file = args.output_path

    with open(training_instances_file, "r") as f:
        training_instances = [json.loads(x) for x in f.readlines()]

    have_api_insts = [
        x
        for x in training_instances
        if x["type"] == "getCompletion:generationAndRequest"
        or x["type"] == "getCompletion:generation"
    ]
    import random
    import re

    random.seed(16)
    sampled = random.sample(have_api_insts, args.cnt)
    blank_reqs = []
    for have_api_inst in sampled:
        cur = have_api_inst.copy()
        cur["context"] = re.sub(
            r"<response>.+", "<response>[]", cur["context"]
        )
        cur["type"] = cur["type"] + "_robust"
        blank_reqs.append(cur)

    random.shuffle(training_instances)
    with open(
        robust_training_instances_file,
        "w",
    ) as f:
        for inst in blank_reqs:
            f.write(json.dumps(inst) + "\n")
