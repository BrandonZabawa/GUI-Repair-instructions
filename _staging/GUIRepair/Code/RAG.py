import os

import faiss
import numpy as np
import openai
from openai import OpenAI

# My API KEY
openai.api_key = ""


client = OpenAI(api_key=openai.api_key)


# 1. Embedding
def get_embedding(text):

    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
        # model="text-embedding-ada-002"
    )
    return response.data[0].embedding


def load_code_files(repo_path):
    code_files = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".js", ".jsx", ".ts", ".tsx", ".scss", ".lua", ".json")):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    code_files[os.path.join(root, file)] = f.read()
    return code_files


def query_doc_file(
    logger, doc_repo_path, doc_files_path, top_k_files, issue_description
):

    all_doc_files_path = [doc_repo_path + doc_path for doc_path in doc_files_path]

    # logger.info(f'Query Files List:\n{all_doc_files_path}')

    code_files = {}
    for doc_file_name in all_doc_files_path:
        with open(doc_file_name, "r", encoding="utf-8") as f:
            try:
                code_files[doc_file_name] = f.read()
            except:
                code_files[doc_file_name] = ""

    embeddings = []
    for file, content in code_files.items():
        embedding = get_embedding(content[:2000])
        embeddings.append(embedding)

    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))

    # issue_description = """blendMode not working when doing point() drawing in webgl"""
    issue_embedding = get_embedding(issue_description)

    D, I = index.search(np.array([issue_embedding]).astype("float32"), k=top_k_files)

    bug_files_rag = []
    # print("Potential bug files:")
    for i in I[0]:
        # print(file_paths[i])
        # bug_files_rag.append(file_paths[i])
        bug_files_rag.append(
            all_doc_files_path[i].replace(doc_repo_path + "/", "").replace("\\", "/")
        )

    return bug_files_rag


def query_bug_file(
    logger, bug_repo_path, no1_bug_file_path_list, top_k_files, issue_description
):

    code_files_dict = {}
    for No1_bug_file_path in no1_bug_file_path_list:
        repo_path = bug_repo_path + "/" + No1_bug_file_path
        code_files = load_code_files(repo_path)
        for file_name in code_files.keys():
            code_files_dict[file_name] = code_files[file_name]

    embeddings = []
    file_paths = list(code_files_dict.keys())

    logger.info(f"Query Files List:\n{file_paths}")

    for file, content in code_files_dict.items():
        embedding = get_embedding(content[:2000])
        embeddings.append(embedding)

    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))

    # issue_description = """blendMode not working when doing point() drawing in webgl"""

    if "Related Documents:" in issue_description:
        issue_description = issue_description.split("Related Documents:")[0]
    issue_embedding = get_embedding(issue_description)

    D, I = index.search(np.array([issue_embedding]).astype("float32"), k=top_k_files)

    bug_files_rag = []
    print("Potential bug files:")
    for i in I[0]:
        # print(file_paths[i])
        # bug_files_rag.append(file_paths[i])
        bug_files_rag.append(
            file_paths[i].replace(bug_repo_path + "/", "").replace("\\", "/")
        )

    return bug_files_rag
