import os
import sys
import json
import argparse
from dot_prompt_transfer import find_first_identifier, coordinates_to_index
from create_training_corpus import point_in_range
from loguru import logger


from tree_sitter import Language, Parser

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--insts", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--type", type=str, choices=["lib", "inner", "mixed"])
    parser.add_argument("--repo_root", type=str)
    parser.add_argument("--cnt", type=int)
    args = parser.parse_args()

    JA_LANGUAGE = Language("../tree_sitter_build/language_set.so", "java")
    parser = Parser()
    parser.set_language(JA_LANGUAGE)

    comp_file = args.insts
    repo_root = args.repo_root
    valid_infer = args.output

    with open(comp_file) as f:
        comp = json.load(f)

    method_decl_query = JA_LANGUAGE.query(
        """
    (method_declaration) @method-declaration
    """
    )
    # file_set = list(comp.keys())
    repo_set = set()
    for file_path, reqs in comp.items():
        relative_file_path = file_path[len(repo_root) :]
        repo_name = relative_file_path.split("/")[0]
        repo_set.add(repo_name)
    repo_set = list(repo_set)

    import random

    random.seed(16)
    results = []
    # valid_file_set = random.sample(file_set, int(len(file_set)*0.1))
    for file_path, reqs in comp.items():
        # if file_path in valid_file_set:
        #     output_file = valid_file
        # else:
        #     output_file = train_file
        relative_file_path = file_path[len(repo_root) :]
        repo_name = relative_file_path.split("/")[0]
        relative_file = relative_file_path[len(repo_name) + 1 :]
        # print(f"Checking {file_path}")

        with open(file_path) as f:
            code = f.read()
        byte_str = bytes(code, "utf8")
        tree = parser.parse(byte_str)
        method_decls = method_decl_query.captures(tree.root_node)
        _method_decls = []

        for idx, method_decl in enumerate(method_decls):
            if idx == 0:
                _method_decls.append(method_decl)
                continue
            if method_decl[0].end_byte > method_decls[idx - 1][0].end_byte:
                _method_decls.append(method_decl)

        method_decls = _method_decls

        for method_decl in method_decls:
            method_decl = method_decl[0]
            body = method_decl.child_by_field_name("body")
            if body is None:
                continue

            start_idx = -1
            for idx, req in enumerate(reqs):
                trigger_point = req["trigger_point"]
                if point_in_range(
                    trigger_point, method_decl.start_point, method_decl.end_point
                ):
                    start_idx = idx
                    break

            if start_idx == -1:
                continue

            for idx, req in enumerate(reqs[start_idx:]):
                trigger_point = req["trigger_point"]
                trigger_byte = req["trigger_byte"]
                full_str = byte_str.decode("utf8")
                method_end_index = coordinates_to_index(
                    full_str, method_decl.end_point[0] + 1, method_decl.end_point[1] + 1
                )
                context = byte_str[:trigger_byte].decode("utf8")
                trigger_index = len(context) - 1
                if point_in_range(
                    trigger_point, method_decl.start_point, method_decl.end_point
                ):
                    completion = full_str[trigger_index + 1 : method_end_index]
                    if completion == "":
                        logger.warning(f"{full_str[trigger_index]}")
                        print(full_str)
                        print(
                            f"Empty completion: {trigger_index}, {method_end_index}, {trigger_point}, {method_decl.start_point}, {method_decl.end_point}"
                        )
                        exit(0)
                    if (
                        args.type == "mixed"
                        or args.type == "lib"
                        and req["lib"] == "true"
                        or args.type == "inner"
                        and req["lib"] == "false"
                    ):
                        results.append(
                            {
                                "repo": repo_name,
                                "classFileName": relative_file,
                                "methodStartIdx": coordinates_to_index(
                                    full_str,
                                    method_decl.start_point[0] + 1,
                                    method_decl.start_point[1] + 1,
                                ),
                                "methodEndIdx": coordinates_to_index(
                                    full_str,
                                    method_decl.end_point[0] + 1,
                                    method_decl.end_point[1] + 1,
                                ),
                                "dot_idx": trigger_byte,
                                "context": context,
                                "next_identifier": find_first_identifier(completion, 0),
                                "method_completion": completion,
                                "line": trigger_point[0],
                                "col": trigger_point[1],
                                "lib": req["lib"],
                            }
                        )
                    # context = byte_str[:trigger_byte].decode("utf8")
                else:
                    # completion = byte_str[last_end_byte:method_decl.end_byte].decode("utf8")
                    # with open(output_file, "a") as f:
                    #     f.write(json.dumps({
                    #         "repo": repo_name,
                    #         "file": relative_file,
                    #         "context": context,
                    #         "completion": completion,
                    #         "type": "getCompletion:generation"
                    #     })+"\n")
                    # instance_cnt += 1
                    break

    results = random.sample(results, args.cnt)
    with open(valid_infer, "w") as f:
        json.dump(results, f, indent=4)
