from tree_sitter import Parser, Language
JA_LANGUAGE = Language("tree_sitter_build/language_set.so", "java")
parser = Parser()
parser.set_language(JA_LANGUAGE)

class Identifier:
    def __init__(self, node, kind="identifier"):
        self.node = node
        self.name = node.text.decode()
        self.start_byte = node.start_byte
        self.end_byte = node.end_byte
        self.start_row = node.start_point[0]
        self.end_row = node.end_point[0]
        self.start_col = node.start_point[1]
        self.end_col = node.end_point[1]
        self.kind = kind

    def __dict__(self):
        return {
            "name": self.name,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "start_row": self.start_row,
            "end_row": self.end_row,
            "start_col": self.start_col,
            "end_col": self.end_col,
            "kind": self.kind
        }
        

def getParsedTree(src):
    bytecodes = bytes(src, "utf8")
    tree = parser.parse(bytecodes)
    return tree

def getIdentifier(tree):
    for child in tree.root_node.children:
        if child.type == "identifier":
            yield child

def getIdentifiersByQuery(tree, queries):
    query_str = "\n".join(queries)
    query = JA_LANGUAGE.query(query_str)
    captures = query.captures(tree.root_node)
    return captures

tree_obj = None
remove_itr = 0
def checkOverlappedIdentifier(identifier_list, identifier):
    global remove_itr
    global tree_obj
    # print(remove_itr)
    for i_idx in range(remove_itr, len(identifier_list)):
        i = identifier_list[i_idx]
        if i.start_byte <= identifier.start_byte and i.end_byte >= identifier.start_byte or i.start_byte <= identifier.end_byte and i.end_byte >= identifier.end_byte:
            remove_itr = i_idx
            return True
        elif i.start_byte > identifier.end_byte:
            remove_itr = i_idx
            return False
    remove_itr = len(identifier_list)
    return False

def getLongIdentifiers(tree):
    queries = [
        """(method_invocation
                object: (_) @dot ?
                name: (_) @dot) @call""",
        """(field_access
                object: (_) @dot
                field: (_) @dot) @field_access""",
    #     """(identifier) @identifier""",
    ]

    queriedLongIdentifier = getIdentifiersByQuery(tree, queries=queries)
    long_identifiers = []
    for idx, long_identifier in enumerate(queriedLongIdentifier):
        if long_identifier[1] == "dot":
            if queriedLongIdentifier[idx-1][1] != "dot":
                long_identifiers.append(Identifier(long_identifier[0]))
            else:
                long_identifiers[-1].name += "." + long_identifier[0].text.decode()
                long_identifiers[-1].end_byte = long_identifier[0].end_byte
                long_identifiers[-1].end_row = long_identifier[0].end_point[0]
                long_identifiers[-1].end_col = long_identifier[0].end_point[1]
        elif long_identifier[1] == "keep_last":
            if queriedLongIdentifier[idx-1][1] != "keep_last":
                long_identifiers.append(Identifier(long_identifier[0]))
            else:
                long_identifiers[-1].name = long_identifier[0].text.decode()
                long_identifiers[-1].end_byte = long_identifier[0].end_byte
                long_identifiers[-1].end_row = long_identifier[0].end_point[0]
                long_identifiers[-1].end_col = long_identifier[0].end_point[1]

    return long_identifiers

def getDeclaredIdentifiers(tree):
    queries = [
        """(class_declaration
                name: (_) @identifier)""",
        """(method_declaration
                name: (_) @identifier)""",
        """(formal_parameter
                name: (_) @identifier)""",
        """(package_declaration (
                scoped_identifier
                    scope: (_) @keep_last ?
                    name: (_) @keep_last
                )) @package""",
        """(import_declaration (
                scoped_identifier
                    scope: (_) @keep_last ?
                    name: (_) @keep_last
                )) @import""",
    ]

    queriedIdentifier = getIdentifiersByQuery(tree, queries=queries)
    identifiers = []
    for identifier in queriedIdentifier:
        identifiers.append(Identifier(identifier[0], kind="declared"))
    return identifiers

def getReferencedIdentifiers(tree, to_remove):
    global remove_itr
    global tree_obj
    if tree != tree_obj:
        itr = 0
        tree_obj = tree

    queries = [
        """(identifier) @identifier""",
    ]

    queriedIdentifier = getIdentifiersByQuery(tree, queries=queries)
    identifiers = []
    for identifier_idx in range(itr, len(queriedIdentifier)):
        identifier = queriedIdentifier[identifier_idx]
        if not checkOverlappedIdentifier(to_remove, Identifier(identifier[0])):
            identifiers.append(Identifier(identifier[0]))
    return identifiers

def getIdentifiers(file):
    with open(file, 'r') as f:
        src = f.read()
    tree = getParsedTree(src)

    long_identifiers = getLongIdentifiers(tree)

    declared_identifiers = getDeclaredIdentifiers(tree)

    to_remove = long_identifiers + declared_identifiers
    to_remove = sorted(to_remove, key=lambda x: x.start_byte)

    identifiers = getReferencedIdentifiers(tree, to_remove)

    return long_identifiers, declared_identifiers, identifiers

def getStrangeIdentifiers(file):
    long_identifiers, declared_identifiers, identifiers = getIdentifiers(file)

    identifier_map = {}

    all_identifiers = long_identifiers + declared_identifiers + identifiers
    sorted(all_identifiers, key=lambda x: x.start_byte)
    for identifier in all_identifiers:
        if identifier.name not in identifier_map:
            identifier_map[identifier.name] = []
        identifier_map[identifier.name].append(identifier)

    strange_identifiers = []
    for identifier in identifier_map:
        for idx, inst in enumerate(identifier_map[identifier]):
            if inst.kind == "declared":
                continue
            if idx == 0:
                strange_identifiers.append(inst)
            elif inst.end_row - identifier_map[identifier][idx-1].end_row > 9999:
                strange_identifiers.append(inst)
            
    return strange_identifiers

repos_dir = "/Users/tannpopo/coding/coding-interfere/repo_to_mine"
import os
import sys
from tqdm import tqdm
import json
from loguru import logger

def getAllJavaFiles(repo_dir):
    java_files = []
    for root, dirs, files in os.walk(repo_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
        for dir in dirs:
            if dir == "target":
                continue
            else:
                dir_path = os.path.join(root, dir)
                java_files.extend(getAllJavaFiles(dir_path))
    return java_files

def getStrangeIdentifiersInRepo(repo_dir):
    strange_identifiers = []
    java_files = getAllJavaFiles(repo_dir)
    logger.info(f"Total {len(java_files)} java files")
    for file in tqdm(java_files):
        cur_identifiers = getStrangeIdentifiers(file)
        for idx, identifier in enumerate(cur_identifiers):
            strange_identifiers.append({
                "file_path": file,
                "strange_identifier": identifier.__dict__(),
            })
    return strange_identifiers

repo_list = os.listdir(repos_dir)
for repository_dir in repo_list:
    if os.path.isfile(f"strange_identifiers/{repository_dir}.json"):
        continue
    logger.info(f"Start {repository_dir}")
    if not os.path.isdir(os.path.join(repos_dir, repository_dir)):
        continue
    strange_identifiers = getStrangeIdentifiersInRepo(os.path.join(repos_dir, repository_dir))
    logger.info(f"Finished {repository_dir}, {len(strange_identifiers)} strange identifiers found")
    with open(f"strange_identifiers/{repository_dir}.json", "w") as f:
        json.dump(strange_identifiers, f, indent=4)