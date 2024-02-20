import os
import sys
import json
import argparse
from tree_sitter import Language, Parser

def point_in_range(point, start, end):
    return start[0] < point[0] < end[0] or ( start[0] < end[0] and ((start[0] == point[0] and start[1] < point[1]) or (point[0] == end[0] and point[1] < end[1]))) or (start[0] == end[0] == point[0] and start[1] <= point[1] and point[1] <= end[1])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--completion_item_corpus", type=str)
    parser.add_argument("--output_path", type=str)
    parser.add_argument("--repo_root", type=str)
    args = parser.parse_args()

    JA_LANGUAGE = Language("../tree_sitter_build/language_set.so", "java")
    parser = Parser()
    parser.set_language(JA_LANGUAGE)

    comp_file = args.completion_item_corpus
    with open(comp_file) as f:
        comp = json.load(f)

    method_decl_query = JA_LANGUAGE.query(
        """
    (method_declaration) @method-declaration
    """
    )
    with open(args.output_path, "w") as f:
        pass

    for file_path, reqs in comp.items():
        repo = file_path.split(args.repo_root)[-1].strip("/").split("/")[0]
        output_file = args.output_path

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
                with open(output_file, "a") as f:
                    f.write(
                        json.dumps(
                            {
                                "dot_id": -1,
                                "repo": repo,
                                "file": file_path,
                                "context": byte_str[: body.start_byte + 1].decode(
                                    "utf8"
                                ),
                                "completion": byte_str[
                                    body.start_byte + 1 : method_decl.end_byte
                                ].decode("utf8"),
                                "type": "no_api_call",
                            }
                        )
                        + "\n"
                    )
                continue

            context = byte_str[: body.start_byte + 1].decode("utf8")
            last_end_byte = body.start_byte + 1
            for idx, req in enumerate(reqs[start_idx:]):
                trigger_point = req["trigger_point"]
                trigger_byte = req["trigger_byte"]
                if point_in_range(
                    trigger_point, method_decl.start_point, method_decl.end_point
                ):
                    completion = (
                        "" if idx == 0 else "</response></request>"
                    ) + byte_str[last_end_byte:trigger_byte].decode("utf8")
                    completion += f"""<request>LSP::getCompletion()<response>"""
                    with open(output_file, "a") as f:
                        f.write(
                            json.dumps(
                                {
                                    "dot_id": req["id"],
                                    "repo": req["repo"],
                                    "file": req["file"],
                                    "context": context,
                                    "completion": completion,
                                    "type": "getCompletion:request"
                                    if idx == 0
                                    else "getCompletion:generationAndRequest",
                                }
                            )
                            + "\n"
                        )
                    context = byte_str[:last_end_byte].decode("utf8")
                    last_end_byte = trigger_byte
                    # context = byte_str[:trigger_byte].decode("utf8")
                    context += (
                        completion.replace("</request>", "") + f"""{req["response"]}"""
                    )
                else:
                    break

            completion = "</response></request>" + byte_str[
                last_end_byte : method_decl.end_byte
            ].decode("utf8")
            with open(output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "dot_id": req["id"],
                            "repo": req["repo"],
                            "file": req["file"],
                            "context": context,
                            "completion": completion,
                            "type": "getCompletion:generation",
                        }
                    )
                    + "\n"
                )
