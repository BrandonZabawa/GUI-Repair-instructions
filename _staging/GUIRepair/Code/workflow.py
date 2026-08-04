import base64
import copy
import io
import json
import os
import re
import subprocess
import time

# from file_level_loc_agent import file_level_locating_agent
from collections import Counter
from difflib import SequenceMatcher
from itertools import chain

import openai
#from Code.multimodal_trans import Image2Code
from multimodal_trans import Image2Code
from numpy import save
from PIL import Image, ImageChops

from build_cmd import make_build_cmd, make_check_cmd
from llm_io_stream import claude_chat, openai_chat
from RAG import query_bug_file
from searching_keywords import bug_file_searching_by_keywords


def read_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def read_file_lines(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.readlines()


def save_file(file_path, data, encoding="utf-8"):
    """Save data to a file with the specified encoding."""
    try:
        with open(file_path, "w", encoding=encoding) as file:
            file.write(data)
    except UnicodeEncodeError as e:
        print(f"Unicode encode error: {e}")
        return "Unicode encode error"


def read_json_file(file_path):
    with open(file_path, "r") as json_file:
        return json.load(json_file)


# def save_json_file(file_path, data):
#     with open(file_path, 'w') as json_file:
#         json.dump(data, json_file, indent=4)


def contains_chinese(obj):
    """check if contrain chinese string"""
    if isinstance(obj, str):
        return bool(re.search(r"[\u4e00-\u9fff]", obj))
    elif isinstance(obj, dict):
        return any(contains_chinese(value) for value in obj.values())
    elif isinstance(obj, (list, tuple, set)):
        return any(contains_chinese(item) for item in obj)
    return False


def save_json_file(file_path, data):
    """save JSON, if contrain chinese string >>> ensure_ascii=False"""
    contains_cn = contains_chinese(data)
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=not contains_cn)


def parse_javascript_file(file_path):
    """Use Node.js script to parse a JS file and extract classes and functions."""
    try:
        if "markedjs" in file_path:
            # because markedjs use some special js coding rules, so we need change parse script
            parse_scripe_file = "parse_js_new.js"
        elif (
            "Automattic" in file_path
            or "highlightjs" in file_path
            or "carbon-design-system" in file_path
        ):
            parse_scripe_file = "parse_js_old_copy.js"
        else:
            parse_scripe_file = "parse_js_old.js"
        result = subprocess.run(
            ["node", parse_scripe_file, file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed_data = json.loads(result.stdout)
        # Specify the encoding explicitly when reading the file
        with open(file_path, "r", encoding="utf-8") as file:
            file_lines = file.read().splitlines()
        return parsed_data["classes"], parsed_data["functions"], file_lines
    except subprocess.CalledProcessError as e:
        # print(f"Error parsing JS file {file_path}: {e.stderr}")
        with open(file_path, "r", encoding="utf-8") as file:
            file_lines = file.read().splitlines()
        return [], [], file_lines
    except UnicodeDecodeError as e:
        print(f"Unicode decode error in file {file_path}: {e}")
        return [], [], []


def create_structure(directory_path, args):
    """Create the structure of the repository directory by parsing JS files."""
    structure = {}

    EXCLUDED_DIRS = {
        "node_modules",
        "test",
        "tests",
        "dist",
        "build",
        "out",
        "auto",
        "coverage",
        "scripts",
        "example",
        "examples",
        ".git",
        ".github",
        "assets",
        ".yarn",
        ".husky",
        "e2e",
        "docs",
    }

    for root, dirs, files in os.walk(directory_path):
        if args.File_Sort == "True":
            # sort dirs
            dirs[:] = sorted(
                [d for d in dirs if d not in EXCLUDED_DIRS]
            )  # ignor non-src dirs
            # sort files
            files = sorted(files)
        else:
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]  # ignor non-src dirs

        # Calculate relative path from root
        relative_root = os.path.relpath(root, directory_path)
        path_parts = relative_root.split(os.sep) if relative_root != "." else []

        # Navigate to the correct level in the structure dictionary
        curr_struct = structure
        for part in path_parts:
            if part not in curr_struct:
                curr_struct[part] = {}
            curr_struct = curr_struct[part]

        # Add files to the current structure level
        for file_name in files:
            if (
                file_name.endswith(".js")
                or file_name.endswith(".js.snap")
                or file_name.endswith(".jsx")
                or file_name.endswith(".ts")
                or file_name.endswith(".tsx")
            ):
                file_path = os.path.join(root, file_name)
                class_info, function_names, file_lines = parse_javascript_file(
                    file_path
                )
                curr_struct[file_name] = {
                    "classes": class_info,
                    "functions": function_names,
                    "text": file_lines,
                }
            elif (
                file_name.endswith(".lua") or file_name.endswith(".R")
            ) and "quarto-dev" in args.output_dir:
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8") as file:
                    file_lines = file.read().splitlines()
                curr_struct[file_name] = {
                    "classes": "",
                    "functions": "",
                    "text": file_lines,
                }
            elif file_name.endswith(".json") and "scratchfoundation" in args.output_dir:
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8") as file:
                    file_lines = file.read().splitlines()
                curr_struct[file_name] = {
                    "classes": "",
                    "functions": "",
                    "text": file_lines,
                }
            elif file_name.endswith(".scss") and "alibaba-fusion" in args.output_dir:
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8") as file:
                    file_lines = file.read().splitlines()
                curr_struct[file_name] = {
                    "classes": "",
                    "functions": "",
                    "text": file_lines,
                }
            elif file_name.endswith(".md") and "alibaba-fusion" in args.output_dir:
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8") as file:
                    file_lines = file.read().splitlines()
                curr_struct[file_name] = {
                    "classes": "",
                    "functions": "",
                    "text": file_lines,
                }
            else:
                curr_struct[file_name] = {}

    return structure


def show_project_structure(structure, args, spacing=0) -> str:
    """pprint the project structure"""

    pp_string = ""

    # sort items
    sorted_items = sorted(
        structure.items(),
        key=lambda item: (
            # 0 if '.' in item[0] else 1,  # before file (0), after dir (1)
            0 if "." not in item[0] else 1,  # before dir, after file
            item[0].lower(),  # sort item name
        ),
    )

    # for key, value in structure.items():
    for key, value in sorted_items:
        if "." in key:
            if ".json" in key and "scratchfoundation" in args.output_dir:
                pass
            if ".json" in key:
                continue
            if (
                ".js" in key
                or ".ts" in key
                or ".js.snap" in key
                or ".jsx" in key
                or ".tsx" in key
                or (".lua" in key and "quarto-dev" in args.output_dir)
                or (".R" in key and "quarto-dev" in args.output_dir)
                or (".scss" in key and "alibaba-fusion" in args.output_dir)
                or (".md" in key and "alibaba-fusion" in args.output_dir)
            ):
                pass
            else:
                continue  # skip none js files
        if "." in key:
            pp_string += " " * spacing + str(key) + "\n"
        else:
            pp_string += " " * spacing + str(key) + "/" + "\n"
        if "classes" not in value:
            pp_string += show_project_structure(value, args, spacing + 4)

    return pp_string


def repair_feedback_prompt_construction(
    bug_image_list, fix_image_list, problem_statement, image_file_list
):
    analyze_bug_scenarios_prompt = f"""
I will give you the Issue Report, you need to analyze the issue scenario to infer what the correct rendering of the effect looks like.
    1. Read the bug report and view the bug scenarion images (if images are available) to analyze the bug scenarion; 
    2. Please expand your analysis based on the screenshot of the bug scenario and infer what the correct rendering of the effect looks like.
    
* Bug Report
'''
{problem_statement}
'''
"""

    analyze_patch_effects_prompt = f"""
I will give you the bug image and patch image, you need to analyze whether the current patch resolved the buggy scenario by comparing the bug and patch images.

* The first picture is the Bug Image
* The second picture is the Patch Image

"""

    system_prompt = """
You are a software testing engineer, you excel at analyzing bug reports and infering what the correct rendering of the effect looks like, in order to help select the valid patch from patch candidates.
First, the user will provide the Bug Report (may attach the issue scenario images), please analyze the issue scenario and infer the correct except behaviors of bug scenario. 
Second, the user will provide the bug image of buggy program and the patch image of patched program, please analyze whether the current patch has solved the bug scenarion and output your answer (YES: solved this bug; NO: unsolved this bug.).

EXAMPLE OUTPUT:
{   
    "bug_analyze": "Analyze the bug scenario and infering what the correct rendering of the effect looks like.",
    "patch_analyze": "Analyze whether the current patch has solved the bug scenario by viewing the bug and patch images.",
    "final_answer": "YES or NO"
}
"""
    user_prompt = {}

    user_prompt["bug_analyze"] = [
        {"type": "text", "text": analyze_bug_scenarios_prompt}
    ] + image_file_list

    user_prompt["fix_analyze"] = (
        [{"type": "text", "text": analyze_patch_effects_prompt}]
        + bug_image_list
        + fix_image_list
    )

    return system_prompt, user_prompt


def keywords_generation_prompt_construction(problem_statement, image_file_list):
    generate_bug_keywords_prompt = f"""
I will give you the bug related information (i.e., Bug Report), you need to analyze what valid information can be obtained from the bug scenario images to help locate the bug files.
    1. Read the bug report and view the bug scenarion images (if images are available) to analyze the bug scenarion; 
    2. Please expand your analysis based on the screenshot of the bug scenario and provide some keywords that may appear in the bug code for bug file search.
    
* Bug Report
'''
{problem_statement}
'''

"""

    system_prompt = """
You are a senior software engineer, you excel at analyzing bug reports and finding key information from bug scenario images to help locate bug files.
The user will provide the Bug Report (may attach the bug images). Please analyze the bug scenario images, then return some keywords may appear in the bug code for bug file search and explain why these keywords may in bug files. 

EXAMPLE INPUT: 

* Bug Report
'''
problem_statement
'''

* Bug Scenario Images
'''
image
'''

EXAMPLE OUTPUT:
{   
    "bug_analyze": "Analyze the bug scenario and find key information by looking the bug images.",
    "bug_keywords": ["keyword_1", "keyword_2", "keyword_3", "keyword_4", "keyword_5", "keyword_6", "keyword_7", "keyword_8", "keyword_9", "keyword_10", "keyword_11", "keyword_...", "keyword_n"],
    "explanation": "Explanation of why these keywords may appear in the bug files."
}
"""

    user_prompt = [
        {
            "type": "text",
            "text": generate_bug_keywords_prompt,
        }
    ]
    user_prompt = user_prompt + image_file_list
    return system_prompt, user_prompt


def all_file_locate_prompt_construction(
    repo_structure, problem_statement, image_file_list, args
):
    obtain_relevant_files_prompt = f"""
I will give you the bug related information (i.e., Bug Report) for your references, you need to find all suspicious bug related files in the code Repo.
    1. Read the bug report and view the bug scenarion images (if images are available) to describe and analyze the bug scenario images; 
    2. Look the Repository Structure to find bug related files that would need to edit to fix the problem; 
    3. Save all bug related files and explain why these files are bug related .
    
* Bug Report
'''
{problem_statement}
'''

* Repository Structure
'''
{repo_structure}
'''

"""

    system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Repository Structure. Please describe the bug scenario images, then return all bug related files and explain why these files are bug related. 

EXAMPLE INPUT: 

* Bug Report
'''
problem_statement
'''

* Repository Structure
'''
repo_structure
'''

* Bug Scenario Images
'''
image
'''

EXAMPLE OUTPUT:
{   
    "bug_scenario": "Description of the bug scenario.",
    "bug_files": ["src/bug_file1.js", "src/path/bug_file2.js", "src/path/bug_file3.js"],
    "explanation": "Explanation of why these files are bug related."
}
"""

    if "claude" in args.base_model:
        system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Repository Structure. Please describe the bug scenario images, then return all bug related files and explain why these files are bug related. 

Note that you need analyze this feedback and output in JSON format with keys: "bug_scenario" (str), "bug_files" (list), and "explanation" (str).

EXAMPLE OUTPUT:
{   
    "bug_scenario": "Description of the bug scenario.", 
    "bug_files": ["src/bug_file1.js", "src/path/bug_file2.js", "src/path/bug_file3.js"], 
    "explanation": "Explanation of why these files are bug related."
}
"""

    user_prompt = [
        {
            "type": "text",
            "text": obtain_relevant_files_prompt,
        }
    ]
    user_prompt = user_prompt + image_file_list
    return system_prompt, user_prompt


def key_file_locate_prompt_construction(
    compressed_bug_files,
    problem_statement,
    image_file_list,
    max_candidate_bug_files,
    args,
):
    if len([key for key in compressed_bug_files.keys()]) > max_candidate_bug_files:
        files_limit_token = f" (at most {max_candidate_bug_files} key bug files) "
    else:
        files_limit_token = " "

    obtain_relevant_files_prompt = f"""
I will give you the bug related information (i.e., Bug Report) for your references, you need to find key bug files{files_limit_token}by looking all Compressed Bug Files.
    1. Read the bug report and view the bug scenarion images (if images are available) to describe the bug scenario images; 
    2. Look all compressed bug files to find key bug files that would need to edit to fix the problem; 
    3. Save all key bug files{files_limit_token}and explain why these files are bug files.
    
* Bug Report
'''
{problem_statement}
'''

* Compressed Bug Files
'''
{compressed_bug_files}
'''

"""

    system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Compressed Bug Files. Please describe the bug scenario images, then return key bug files and explain why these files are bug files. 
Explain of Compressed Bug Files: Directly providing the complete context of all files can be large. As such, we build a compressed format of each file that contains the list of class, function, or variable declarations. We refer to this format as the skeleton format. In the skeleton format, we provide only the headers of the classes and functions in the file. For classes, we further include any class fields and methods (signatures only). Additionally, we also keep comments in the class and module level to provide further information. Compared to providing the entire file context to the model, the skeleton format is a much more concise representation, especially when the file contains thousands of lines, making it impractical/costly to process all at once with existing LLMs.

EXAMPLE INPUT: 

* Bug Report
'''
problem_statement
'''

* Compressed Bug Files
'''
compressed_bug_files
'''

* Bug Scenario Images
'''
image
'''

EXAMPLE OUTPUT:
{   
    "bug_scenario": "Description of the bug scenario.",
    "bug_files": ["src/bug_file1.js", "src/path/bug_file2.js", "src/path/bug_file3.js"],
    "explanation": "Explanation of why these files are bug files."
}
"""

    if "claude" in args.base_model:
        system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Compressed Bug Files. Please describe the bug scenario images, then return key bug files and explain why these files are bug files. 
Explain of Compressed Bug Files: Directly providing the complete context of all files can be large. As such, we build a compressed format of each file that contains the list of class, function, or variable declarations. We refer to this format as the skeleton format. In the skeleton format, we provide only the headers of the classes and functions in the file. For classes, we further include any class fields and methods (signatures only). Additionally, we also keep comments in the class and module level to provide further information. Compared to providing the entire file context to the model, the skeleton format is a much more concise representation, especially when the file contains thousands of lines, making it impractical/costly to process all at once with existing LLMs.

Note that you need analyze this feedback and output in JSON format with keys: "bug_scenario" (str), "bug_files" (list), and "explanation" (str).

EXAMPLE OUTPUT:
{   
    "bug_scenario": "Description of the bug scenario.",
    "bug_files": ["src/bug_file1.js", "src/path/bug_file2.js", "src/path/bug_file3.js"],
    "explanation": "Explanation of why these files are bug files."
}
"""

    user_prompt = [
        {
            "type": "text",
            "text": obtain_relevant_files_prompt,
        }
    ]
    user_prompt = user_prompt + image_file_list
    return system_prompt, user_prompt


def key_class_function_locate_prompt_construction(
    compressed_key_bug_files, problem_statement, image_file_list, args
):
    obtain_relevant_files_prompt = f"""
I will give you the bug related information (i.e., Bug Report) for your references, you need to find key bug classes/functions by looking all Compressed Bug Files.
    1. Read the bug report and view the bug scenarion images (if images are available) to describe the bug scenario images; 
    2. Look all compressed bug files to find key bug classes or functions that would need to edit to fix the problem; 
    3. Save all key bug classes or functions and explain why these classes or functions are bug related elements.
    
* Bug Report
'''
{problem_statement}
'''

* Compressed Bug Files
'''
{compressed_key_bug_files}
'''

"""

    system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Compressed Bug Files. Please describe the bug scenario images, then return key bug classes/functions and explain why these classes/functions are bug related elements. 
Explain of Compressed Bug Files: Directly providing the complete context of all files can be large. As such, we build a compressed format of each file that contains the list of class, function, or variable declarations. We refer to this format as the skeleton format. In the skeleton format, we provide only the headers of the classes and functions in the file. For classes, we further include any class fields and methods (signatures only). Additionally, we also keep comments in the class and module level to provide further information. Compared to providing the entire file context to the model, the skeleton format is a much more concise representation, especially when the file contains thousands of lines, making it impractical/costly to process all at once with existing LLMs.
Note that if bug code snippets not in class/function or there are not class/function, only output the bug_file_name is enough.

EXAMPLE INPUT: 

* Bug Report
'''
problem_statement
'''

* Compressed Bug Files
'''
compressed_bug_files
'''

* Bug Scenario Images
'''
image
'''

EXAMPLE OUTPUT:
{   
    "bug_scenario": "Description of the bug scenario.",
    "bug_classes": ["bug_file_name//class_name_1", "bug_file_name//class_name_2", "bug_file_name//class_name_3"],
    "bug_functions": ["bug_file_name//function_name_1", "bug_file_name//function_name_2", "bug_file_name//function_name_3"],
    "explanation": "Explanation of why these classes/functions are bug code elements."
}
"""

    if "claude" in args.base_model:
        system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Compressed Bug Files. Please describe the bug scenario images, then return key bug classes/functions and explain why these classes/functions are bug related elements. 
Explain of Compressed Bug Files: Directly providing the complete context of all files can be large. As such, we build a compressed format of each file that contains the list of class, function, or variable declarations. We refer to this format as the skeleton format. In the skeleton format, we provide only the headers of the classes and functions in the file. For classes, we further include any class fields and methods (signatures only). Additionally, we also keep comments in the class and module level to provide further information. Compared to providing the entire file context to the model, the skeleton format is a much more concise representation, especially when the file contains thousands of lines, making it impractical/costly to process all at once with existing LLMs.
If bug code snippets not in class/function or there are not class/function, only output the bug_file_name is enough.

Note that you need analyze this feedback and output in JSON format with keys: "bug_scenario" (str), "bug_classes" (list), "bug_functions" (list), and "explanation" (str).

EXAMPLE OUTPUT:
{   
    "bug_scenario": "Description of the bug scenario.",
    "bug_classes": ["bug_file_name//class_name_1", "bug_file_name//class_name_2", "bug_file_name//class_name_3"],
    "bug_functions": ["bug_file_name//function_name_1", "bug_file_name//function_name_2", "bug_file_name//function_name_3"],
    "explanation": "Explanation of why these classes/functions are bug code elements."
}
"""

    user_prompt = [
        {
            "type": "text",
            "text": obtain_relevant_files_prompt,
        }
    ]
    user_prompt = user_prompt + image_file_list
    return system_prompt, user_prompt


def line_level_class_function_locate_prompt_construction(
    bug_files_with_context_dict, problem_statement, image_file_list
):
    obtain_relevant_files_prompt = f"""
I will give you the bug related information (i.e., Bug Report) for your references, you need to find line-level bug locations by looking all Bug Files.
    1. Read the bug report and view the bug scenarion images (if images are available) to describe the bug scenario images; 
    2. Look all bug files to find key line-level bug locations that would need to edit to fix the problem; 
    3. Save all line numbers of bug locations and explain why code lines are bug related elements.
    
* Bug Report
'''
{problem_statement}
'''

* Bug Files
'''
{bug_files_with_context_dict}
'''

"""

    system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Bug Files. Please describe the bug scenario images, then return key line-level bug locations and explain why these code lines are bug related elements. 
Note that we will use dict format to record Bug Files, the dict's key is the bug file path, and the dict's value is the bug code snippets with the line number.
Note that you need output the bug line number of bug files. If there is no bug locations for the current bug file, only output the empty list.

EXAMPLE INPUT: 

* Bug Report
'''
problem_statement
'''

* Bug Files
'''
{
    "bug_file_path_1": bug_code_snippets,
    "bug_file_path_2": bug_code_snippets,
    "bug_file_path_3": bug_code_snippets
}
'''

* Bug Scenario Images
'''
image
'''

EXAMPLE OUTPUT:
{   
    "bug_locations": {
        "bug_file_path_1": [100, 101, 102, 103],
        "bug_file_path_2": [22, 106, 139],
        "bug_file_path_3": []
    },
    "explanation": "Explanation of why these bug lines are bug code elements."
}
"""

    user_prompt = [
        {
            "type": "text",
            "text": obtain_relevant_files_prompt,
        }
    ]
    user_prompt = user_prompt + image_file_list
    return system_prompt, user_prompt


def patch_generation_prompt_construction(
    bug_files_with_context_dict, problem_statement, image_file_list
):
    generate_patches_prompt = f"""
I will give you the bug related information (i.e., Bug Report) for your references, you need to generate patches (*SEARCH/REPLACE* edits) by looking all Bug Code Snippets.
    1. Read the bug report and view the bug scenarion images (if images are available) to describe the bug scenario images and reasonning the bug root causes; 
    2. Look all bug snippets files in "* Bug Code Snippets" to analyze and locate bug locations that would need to edit to fix the problem; 
    3. Generate patches for bug files in "* Bug Code Snippets" to fix the current bug. (!!! Note that don't try to fix the reproduce code in Bug Report!!!)
    
 
* Bug Report
'''
{problem_statement}
'''

* Bug Code Snippets
'''
{bug_files_with_context_dict}
'''

"""

    system_prompt = """
The user will provide the Bug Report (may attach the bug images) and Bug Code Snippets. Please analyze the bug scenario images to infer possible bug root cause, then locate the bug locations and generate patches for "* Bug Code Snippets". 
Explain of Bug Code Snippets: We'll provide the key bug code snippets from the bug file, for the rest of the code sections we use ... to omit.
Note that we will use dict format to record Bug Code Snippets, the dict's key is the bug file path, and the dict's value is the bug code snippets.

EXAMPLE INPUT: 

* Bug Report
'''
problem_statement
'''

* Bug Code Snippets
'''
{
    "bug_file_path 1": "bug_code_snippets",
    "bug_file_path 2": "bug_code_snippets",
    "bug_file_path 3": "bug_code_snippets"
}
'''

* Bug Scenario Images
'''
image
'''


Please first localize the bug based on the issue statement, and then generate *SEARCH/REPLACE* edits (i.e., patches) to fix the issue.

Every *SEARCH/REPLACE* edit must use this format:
1. The bug file path (Please give the specific bug file path in "* Bug Code Snippets", e.g., src/components/Image/ImageSearch.js. Not the reproduce code file.)
2. The start of search block: <<<<<<< SEARCH
3. A contiguous chunk of lines to search for in the existing source code
4. The dividing line: =======
5. The lines to replace into the source code
6. The end of the replace block: >>>>>>> REPLACE

EXAMPLE OUTPUT:
(Here is a *SEARCH/REPLACE* edit example)

```javascript
### bug_file_path 2
<<<<<<< SEARCH
from flask import Flask
from transformer import generate
from transformer import train
=======
import math
from flask import Flask
from transformer import generate
from transformer import train
>>>>>>> REPLACE
```

Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Please note that you must provide sufficient *SEARCH* edit context (No less than 3 lines of code) to ensure that the code location can be successfully searched!
Please note that you can't use "/* ~~~~~~~~~~~~~~~~~~~~ */" or "..." to alter and ignore the original code content, you must keep the original code format and content in the *SEARCH/REPLACE* edit!
Wrap the *SEARCH/REPLACE* edit in blocks ```javascript...```.


"""

    # EXAMPLE OUTPUT:
    # {
    #     "bug_file_path 1": "*SEARCH/REPLACE* edits",
    #     "bug_file_path 2": "*SEARCH/REPLACE* edits"
    # }

    user_prompt = [
        {
            "type": "text",
            "text": generate_patches_prompt,
        }
    ]
    # user_prompt = user_prompt + image_file_list
    user_prompt = image_file_list + user_prompt
    return system_prompt, user_prompt


def patch_check_prompt_construction(bug_files_with_context_dict, error_message, patch):
    generate_patches_prompt = f"""
I have generated a patch for a bug file, but this patch introduces compilation errors. Could you please read the original bug file and help me refine the current patch to avoid introducing compilation errors based on the error messages reported after patching.
Finally, you need to output the Refined Patch, which should solve the compilation errors.

* Original Bug Files
'''
{bug_files_with_context_dict}
'''

* Patch
'''
{patch}
'''

* Error Message
'''
{error_message}
'''

"""

    system_prompt = """
Note that we will use dict format to record Patch, the dict's key 'SEARCH' is the bug code, 'REPLACE' is the replaced fix code.

EXAMPLE INPUT: 

* Original Bug Files
'''
bug_files_content
'''

* Patch
'''
"packages/react/src/bug_file.js": [
    {
        "SEARCH": [
            "const mergeRefs = (keyword) => {"
        ],
        "REPLACE": [
            "const mergeRefs = forwardRef((keyword, ref) => {"
        ]
    },
    {
        "SEARCH": [
            "ref={mergeRefs(textInput)}"
        ],
        "REPLACE": [
            "ref={mergeRefs(ref, textInput)}"
        ]
    }
]
'''

* Error Message
'''
error_message
'''


EXAMPLE OUTPUT:

* Refined Patch
'''
"packages/react/src/bug_file.js": [
    {
        "SEARCH": [
            "const mergeRefs = (keyword) => {"
        ],
        "REPLACE": [
            "const mergeRefs = forwardRef((keyword, ref) => {"
        ]
    },
    {
        "SEARCH": [
            "ref={mergeRefs(textInput)}"
        ],
        "REPLACE": [
            "ref={mergeRefs(ref, textInput)}"
        ]
    },
    {
        "SEARCH": [
            "return result",
            "};"
        ],
        "REPLACE": [
            "const context = getthecontext();",
            ")};"
        ]
    }
]
'''

"""

    user_prompt = [
        {
            "type": "text",
            "text": generate_patches_prompt,
        }
    ]

    user_prompt = user_prompt
    return system_prompt, user_prompt


MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB


def encode_image_claude(image_path):
    # print('Pre-processing Claude Images...')
    def compress_image(image_path, format):
        img = Image.open(image_path)
        buffer = io.BytesIO()
        for quality in range(95, 10, -5):
            buffer.seek(0)
            buffer.truncate()
            img.save(buffer, format=format, quality=quality, optimize=True)
            if buffer.tell() <= MAX_IMAGE_SIZE:
                return buffer.getvalue()
        raise ValueError(f"Error: {image_path}")

    # get the image size
    file_size = os.path.getsize(image_path)
    ext = image_path.split(".")[-1].lower()
    img_format = "JPEG" if ext in ["jpg", "jpeg"] else ext.upper()

    if file_size > MAX_IMAGE_SIZE:
        # print(f"preprocessing image: {image_path}")
        compressed_data = compress_image(image_path, img_format)
        return base64.b64encode(compressed_data).decode("utf-8")
    else:
        # print(f"IMAGE_SIZE = {file_size}")
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_bug_scenarion_images(image_sets_path, args):
    # print(image_sets_path)
    image_file_list = []
    if os.path.isdir(image_sets_path):  # is dir
        image_file_list = os.listdir(image_sets_path)
    else:  # not dir, is file path
        image_file_list = [image_sets_path]
    # print(image_file_list)

    if image_file_list is not None:
        for index, image_file in enumerate(image_file_list):
            if os.path.isdir(image_sets_path):
                image_path = os.path.join(
                    image_sets_path, image_file
                )  # Path to your image
            else:
                image_path = image_file

            image_type = "png"
            if "png" in image_path:
                image_type = "png"
            elif "jpg" in image_path:
                image_type = "jpg"
                if "claude" in args.base_model:
                    image_type = "jpeg"
            elif "jpeg" in image_path:
                image_type = "jpeg"
            elif "gif" in image_path:
                image_type = "gif"
            else:
                image_type = image_path.split(".")[-1].strip()

            if "gpt" in args.base_model or "o4-mini" in args.base_model:
                base64_image = encode_image(image_path)  # Getting the Base64 string
                image_file_list[index] = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_type};base64,{base64_image}"
                    },
                }
            elif "claude" in args.base_model:
                base64_image = encode_image_claude(image_path)
                image_file_list[index] = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{image_type}",
                        "data": base64_image,
                    },
                }

    return image_file_list


def compressing_javascript_file(bug_file_structure_dict, save_variable_declaration):
    """
    Preprocess a JavaScript file to create a compressed skeleton format.

    Args:
        file_content (str): The content of the JavaScript file.

    Returns:
        str: A string representing the skeleton format of the JavaScript file.
    """
    # print(bug_file_structure_dict)
    classes_list = bug_file_structure_dict["classes"]
    functions_list = bug_file_structure_dict["functions"]
    text_list = bug_file_structure_dict["text"]

    compressed_text_list = ["" for i in text_list]

    if classes_list != []:
        for class_dict in classes_list:
            class_name = class_dict["name"]
            class_start_line = class_dict["start_line"]
            class_end_line = class_dict["end_line"]

            compressed_text_list[class_start_line - 1] = text_list[class_start_line - 1]
            compressed_text_list[class_end_line - 1] = text_list[class_end_line - 1]

            methods_list = class_dict["methods"]

            if methods_list != []:
                for method_dict in methods_list:
                    method_name = method_dict["name"]
                    method_start_line = method_dict["start_line"]
                    method_end_line = method_dict["end_line"]

                    compressed_text_list[method_start_line - 1] = text_list[
                        method_start_line - 1
                    ]
                    compressed_text_list[method_end_line - 1] = text_list[
                        method_end_line - 1
                    ]

    if functions_list != []:
        for function_dict in functions_list:
            function_name = function_dict["name"]
            function_start_line = function_dict["start_line"]
            function_end_line = function_dict["end_line"]

            compressed_text_list[function_start_line - 1] = text_list[
                function_start_line - 1
            ]
            compressed_text_list[function_end_line - 1] = text_list[
                function_end_line - 1
            ]

            line_no = function_start_line - 1
            loop_times = 0
            while 1:
                if loop_times > 20:
                    break
                if len(text_list[line_no].strip()) > 0:
                    if (
                        text_list[line_no].strip()[-1] == "{"
                        or text_list[line_no].strip()[-1] == "}"
                        or text_list[line_no].strip()[-2:] == "};"
                    ):
                        break
                    else:
                        loop_times += 1
                        line_no += 1
                        compressed_text_list[line_no] = text_list[line_no]
                else:
                    break

    # print(compressed_text_list)

    for index, text in enumerate(text_list):
        text_strip = text.strip()
        # Check if the text is a JavaScript code comment, and save it if it is
        if (
            text_strip.startswith("//")
            or text_strip.startswith("/*")
            or text_strip.endswith("*/")
            or text_strip.startswith("*")
            or text_strip.startswith("import")
            or text_strip.startswith("export")
        ):
            compressed_text_list[index] = text

        # Check if the text is a variable declaration, please save it

        if save_variable_declaration is True:
            if (
                text_strip.startswith("let ")
                or text_strip.startswith("const ")
                or text_strip.startswith("var ")
            ):
                compressed_text_list[index] = text

    # print(compressed_text_list)

    # Remove extra blank lines, leaving only one blank line if there are more than two consecutive blank lines.
    compressed_text_list = [
        line
        for index, line in enumerate(compressed_text_list)
        if not (
            line == ""
            and (index > 0 and compressed_text_list[index - 1] == "")
            and (index > 1 and compressed_text_list[index - 2] == "")
        )
    ]

    for index, compressed_text in enumerate(compressed_text_list):
        compressed_text_list[index] = compressed_text + "\n"

    return compressed_text_list


def get_bug_file_structure_dict(bug_file, repo_structure_dict):
    bug_file_structure_dict = repo_structure_dict
    for key in bug_file.split("/"):
        bug_file_structure_dict = bug_file_structure_dict[key]

    return bug_file_structure_dict


def remove_blank_lines(bug_files_with_context_dict, blank_str, with_line_number):
    for file_path, lines in bug_files_with_context_dict.items():
        # Retain only one blank line if there are multiple consecutive blank lines
        new_lines = []
        for index, line in enumerate(lines):
            if line.strip() == blank_str:
                if not new_lines or new_lines[-1].strip() != blank_str:
                    new_lines.append(line)
            else:
                if with_line_number is True:
                    new_lines.append(f"{index + 1}: {line}")
                else:
                    new_lines.append(line)
        bug_files_with_context_dict[file_path] = new_lines
    return bug_files_with_context_dict


def split_js_code_safely(code_str):
    lines = []
    current_line = ""

    inside_string = False
    string_delimiter = ""
    escape = False
    inside_regex = False

    i = 0
    while i < len(code_str):
        char = code_str[i]

        if inside_string:
            if char == "\\":
                escape = not escape
            elif char == string_delimiter and not escape:
                inside_string = False
            else:
                escape = False
            current_line += char

        elif inside_regex:
            if char == "/" and not escape:
                inside_regex = False
            elif char == "\\":
                escape = not escape
            else:
                escape = False
            current_line += char

        else:
            if char in "\"'":
                inside_string = True
                string_delimiter = char
                escape = False

            elif char == "/" and i > 0 and code_str[i - 1] in " =(,{[":
                inside_regex = True

            elif char == "\n":
                lines.append(current_line)
                current_line = ""
                i += 1
                continue

            current_line += char

        i += 1

    if current_line:
        lines.append(current_line)

    return [line.rstrip() for line in lines]


def extract_patch_edits(patch_content, repo, check_pattern):
    # Initialize a dictionary to store extracted patches
    extracted_edits = {}

    # Regular expression to match the patch edit blocks
    patch_regex = r"```javascript\n### (?P<file_path>.+?)\n(?P<patch_edits>.*?)\n```"
    # Find all matches in the patch content
    matches = re.finditer(patch_regex, patch_content, re.DOTALL)

    if "javascript\n###" not in patch_content:
        # logger.info("extract error. please check patch_content")
        patch_regex = (
            r"```javascript\n(?P<file_path>.+?)\n(?P<patch_edits>.*?)(?=\n```)"
        )
        matches = list(re.finditer(patch_regex, patch_content, re.DOTALL))

    for match in matches:
        file_path = match.group("file_path").strip()
        patch_edits = match.group("patch_edits").strip()

        # Initialize a list to store multiple edits for the same file
        if file_path not in extracted_edits.keys():
            extracted_edits[file_path] = []

        # Regular expression to match each SEARCH/REPLACE block
        edit_regex = r"<<<<<<< SEARCH\n(?P<search>.*?)\n=======\n(?P<replace>.*?)\n>>>>>>> REPLACE"
        edit_matches = re.finditer(edit_regex, patch_edits, re.DOTALL)

        for edit_match in edit_matches:
            edit_search = edit_match.group("search")
            edit_replace = edit_match.group("replace")

            # post-processing code format
            if "PrismJS" in repo or "highlightjs" in repo or "Automattic" in repo:
                if check_pattern == "":
                    extracted_edits[file_path].append(
                        {
                            "SEARCH": [
                                line.strip() for line in edit_search.split("\n")
                            ],
                            "REPLACE": [
                                line.strip() for line in edit_replace.split("\n")
                            ],
                        }
                    )
                elif check_pattern == "\n":
                    extracted_edits[file_path].append(
                        {
                            "SEARCH": [
                                line.strip()
                                for line in split_js_code_safely(edit_search)
                            ],
                            "REPLACE": [
                                line.strip()
                                for line in split_js_code_safely(edit_replace)
                            ],
                        }
                    )
                elif check_pattern == "\\\\":
                    edit_search = edit_search.replace("\\\\", "\\")
                    edit_replace = edit_replace.replace("\\\\", "\\")
                    extracted_edits[file_path].append(
                        {
                            "SEARCH": [
                                line.strip() for line in edit_search.split("\n")
                            ],
                            "REPLACE": [
                                line.strip() for line in edit_replace.split("\n")
                            ],
                        }
                    )
                    # extracted_edits[file_path].append({"SEARCH": [line.strip() for line in split_js_code_safely(edit_search)], "REPLACE": [line.strip() for line in split_js_code_safely(edit_replace)]})
                elif check_pattern == "\\t":
                    edit_search = edit_search.replace("\\t", "\t")
                    edit_replace = edit_replace.replace("\\t", "\t")
                    extracted_edits[file_path].append(
                        {
                            "SEARCH": [
                                line.strip() for line in edit_search.split("\n")
                            ],
                            "REPLACE": [
                                line.strip() for line in edit_replace.split("\n")
                            ],
                        }
                    )
                    # extracted_edits[file_path].append({"SEARCH": [line.strip() for line in split_js_code_safely(edit_search)], "REPLACE": [line.strip() for line in split_js_code_safely(edit_replace)]})
                elif check_pattern == "\\\\and\\t":
                    edit_search = edit_search.replace("\\\\", "\\").replace("\\t", "\t")
                    edit_replace = edit_replace.replace("\\\\", "\\").replace(
                        "\\t", "\t"
                    )
                    extracted_edits[file_path].append(
                        {
                            "SEARCH": [
                                line.strip() for line in edit_search.split("\n")
                            ],
                            "REPLACE": [
                                line.strip() for line in edit_replace.split("\n")
                            ],
                        }
                    )
                    # extracted_edits[file_path].append({"SEARCH": [line.strip() for line in split_js_code_safely(edit_search)], "REPLACE": [line.strip() for line in split_js_code_safely(edit_replace)]})

            else:
                extracted_edits[file_path].append(
                    {
                        "SEARCH": [line.strip() for line in edit_search.split("\n")],
                        "REPLACE": [line for line in edit_replace.split("\n")],
                    }
                )

            # else:
            # extracted_edits[file_path].append({"SEARCH": [line.strip() for line in edit_search.split('\n')], "REPLACE": [line.strip() for line in edit_replace.split('\n')]})

    return extracted_edits


def back_fill_patch(patch_edits, instance_repo_path, repo_structure_dict, logger):
    for bug_file in patch_edits.keys():
        logger.info(f"Backfill: {bug_file}")
        patch_edits_list = patch_edits[bug_file]

        bug_file_path = os.path.join(instance_repo_path, bug_file)

        try:
            bug_file_structure_dict = get_bug_file_structure_dict(
                bug_file, repo_structure_dict
            )
            bug_file_content = bug_file_structure_dict["text"]
            logger.info("get Backfill src file")
        except:
            if os.path.exists(bug_file_path):
                bug_file_content = [
                    line.rstrip("\n") for line in read_file_lines(bug_file_path)
                ]
                logger.info(f"get not exist Backfill src file: {bug_file_path}")
            else:
                logger.info(f"Backfill Bug File path not exist: {bug_file}")
                continue

        pre_file_content = pre2bug(
            patch_edits_list, bug_file_content, bug_file_path, logger
        )  # backfill predicted patch to bug file, get the pre file


def pre2bug(patch_edits_list, bug_file_content, bug_file_path, logger):

    pre_file_content = copy.deepcopy(bug_file_content)
    positions = []

    # First：find all patch edit locations
    # Iterate over each patch edit
    for patch_edit in patch_edits_list:
        search_lines = patch_edit["SEARCH"]
        replace_lines = patch_edit["REPLACE"]
        back_fill_result = "Fail"
        # Find the start index of the search lines in the bug file content
        for i in range(len(bug_file_content) - len(search_lines) + 1):
            if [
                line.strip() for line in bug_file_content[i : i + len(search_lines)]
            ] == search_lines:
                # Replace the search lines with the replace lines
                # pre_file_content[i:i + len(search_lines)] = replace_lines
                positions.append((i, patch_edit))
                # logger.info('A Pre2Bug Success')
                back_fill_result = "Success"
                break

        if back_fill_result == "Fail":
            for i in range(len(bug_file_content) - len(search_lines) + 1):
                if [
                    line.replace("\\", "").strip()
                    for line in bug_file_content[i : i + len(search_lines)]
                ] == [line.replace("\\", "").strip() for line in search_lines]:
                    # Replace the search lines with the replace lines
                    # pre_file_content[i:i + len(search_lines)] = replace_lines
                    positions.append((i, patch_edit))
                    # logger.info('A Pre2Bug Success (remove \\)')
                    back_fill_result = "Success (remove \\)"
                    break

        if back_fill_result == "Fail":
            for i in range(len(bug_file_content) - len(search_lines) + 1):
                search_str = "\n".join([line.strip() for line in search_lines])
                replace_str = "\n".join(
                    [
                        line.strip()
                        for line in bug_file_content[i : i + len(search_lines)]
                    ]
                )
                similarity = SequenceMatcher(None, search_str, replace_str).ratio()
                if similarity >= 0.9:
                    # Replace the search lines with the replace lines
                    # pre_file_content[i:i + len(search_lines)] = replace_lines
                    positions.append((i, patch_edit))
                    # logger.info('A Pre2Bug Success (remove \\)')
                    back_fill_result = f"Success (similarity {similarity})"
                    break

        if back_fill_result == "Fail":
            for i in range(len(bug_file_content) - len(search_lines) + 1):
                if [
                    line.strip()
                    for line in bug_file_content[i : i + len(search_lines)]
                    if "\\" not in line
                ] == [line.strip() for line in search_lines if "\\" not in line]:
                    # Replace the search lines with the replace lines
                    # pre_file_content[i:i + len(search_lines)] = replace_lines
                    positions.append((i, patch_edit))
                    back_fill_result = "Success (skip \\)"
                    break

        logger.info(f"A Pre2Bug {back_fill_result}")

    # Second：Relace all edit postions
    for i, patch_edit in sorted(positions, key=lambda x: x[0], reverse=True):
        search_lines = patch_edit["SEARCH"]
        replace_lines = patch_edit["REPLACE"]

        pre_file_content[i : i + len(search_lines)] = replace_lines
        logger.info(f"Patch applied successfully at line {i}")

    # Join the modified list back into a single string
    # pre_file_content = bug_file_content
    pre_file_content = "\n".join(pre_file_content)
    # print(patch_edits_list)
    save_file(bug_file_path, pre_file_content + "\n")

    return pre_file_content


def get_all_file_paths(repo_structure_dict, current_path=""):
    """
    get repo_structure_dict file path, retrun all file paths

    :param repo_structure_dict: dict, repo dir
    :param current_path: str, current path
    :return: list, all file paths
    """
    file_paths = []

    for key, value in repo_structure_dict.items():
        if isinstance(value, dict):
            file_paths.extend(get_all_file_paths(value, current_path + "/" + key))
        else:
            file_paths.append(current_path)

    return file_paths


def remove_first_dir(path, remove_dir):
    parts = path.split(os.sep)
    if len(parts) > remove_dir:
        return os.path.join(*parts[remove_dir:])
    return path


# check all bug file path
def check_bug_files_path(bug_files_dict, repo_structure_dict):
    all_files_list = get_all_file_paths(repo_structure_dict)
    all_files_list = list(set(all_files_list))
    all_files_list = [file[1:] for file in all_files_list]
    # print(all_files_list)

    for index in bug_files_dict:
        bug_files_list = bug_files_dict[index]["bug_files"]
        new_bug_files_list = []

        for bug_file in bug_files_list:
            if "." not in bug_file:
                continue

            find_result = "no"
            if bug_file in all_files_list:
                new_bug_files_list.append(bug_file)
                find_result = "yes"
                continue
            else:
                for iter_file in all_files_list:
                    if bug_file in iter_file:
                        new_bug_files_list.append(iter_file)
                        find_result = "yes"
                        break
            # remove incorrent first level dir if is doesn't work
            if find_result == "no":
                bug_file_slice = remove_first_dir(bug_file, remove_dir=1)
                # print(bug_file_slice)
                for iter_file in all_files_list:
                    if bug_file_slice in iter_file:
                        new_bug_files_list.append(iter_file)
                        find_result = "yes"
                        break
            # remove incorrent second level dir if is doesn't work
            if find_result == "no":
                bug_file_slice = remove_first_dir(bug_file, remove_dir=2)
                # print(bug_file_slice)
                for iter_file in all_files_list:
                    if bug_file_slice in iter_file:
                        new_bug_files_list.append(iter_file)
                        find_result = "yes"
                        break
            # remove incorrent third level dir if is doesn't work
            if find_result == "no":
                bug_file_slice = remove_first_dir(bug_file, remove_dir=3)
                # print(bug_file_slice)
                for iter_file in all_files_list:
                    if bug_file_slice in iter_file:
                        new_bug_files_list.append(iter_file)
                        find_result = "yes"
                        break
            # remove incorrent fourth level dir if is doesn't work
            if find_result == "no":
                bug_file_slice = remove_first_dir(bug_file, remove_dir=4)
                # print(bug_file_slice)
                for iter_file in all_files_list:
                    if bug_file_slice in iter_file:
                        new_bug_files_list.append(iter_file)
                        find_result = "yes"
                        break
        # if new_bug_files_list == []:

        bug_files_dict[index]["bug_files"] = new_bug_files_list
    return bug_files_dict, all_files_list


def file_level_locating_val(
    instance_id, instance_repo_path, instance_info, args, logger
):
    repo = instance_info["repo"]
    base_commit = instance_info["base_commit"]
    problem_statement = instance_info["problem_statement"]

    # problem_statement = decode_if_unicode(problem_statement)  # parse Unicode
    # logger.info(f'{problem_statement}')

    token_usage_dict = {}

    # get bug scenarion images
    try:
        image_file_list = get_bug_scenarion_images(
            os.path.join(
                args.repo_path,
                args.dataset_split,
                instance_id.split("__")[0],
                instance_id,
                "IMAGE",
            ),
            args,
        )
    except Exception as e:
        logger.info(f"{e}")
        image_file_list = []

    # Image2Code: generating reproduce code about the bug scenarion/image
    Web_Repo_list = [
        "alibaba-fusion/next",
        "carbon-design-system/carbon",
        "eslint/eslint",
        "grommet/grommet",
        "bpmn-io/bpmn-js",
        "prettier/prettier",
        "quarto-dev/quarto-cli",
        "GoogleChrome/lighthouse",
        "chartjs/Chart.js",
        "processing/p5.js",
    ]
    if args.Code_Reply == "True" and repo in Web_Repo_list:
        user_reproduce_code_file_path = os.path.join(
            args.repo_path,
            args.dataset_split,
            instance_id.split("__")[0],
            instance_id,
            "BUG",
            "reproduce_code.txt",
        )
        # if os.path.isfile(user_reproduce_code_file_path): # if issue report provides the reproduce code url or text
        #     logger.info(f'Issue Reprot has provided Reproduce Code or LLM has genereated Reproduce Code.')
        #     reproduce_code = read_file(user_reproduce_code_file_path)
        #     doc_files_dict, compressed_doc_files_dict, doc_files_content = {}, {}, ""

        # else:  # if no reproduce code
        (
            reproduce_code_dict,
            reproduce_code,
            doc_files_dict,
            compressed_doc_files_dict,
            doc_files_content,
            token_usage_dict,
        ) = Image2Code(
            logger,
            args,
            repo,
            instance_id,
            instance_repo_path,
            token_usage_dict,
            problem_statement,
            image_file_list,
        )
        # save_file(user_reproduce_code_file_path, reproduce_code)

        if os.path.isfile(
            user_reproduce_code_file_path
        ):  # if issue report provides the reproduce code url or text
            logger.info(f"Issue Reprot has provided Reproduce Code.")
            reproduce_code = read_file(user_reproduce_code_file_path)

        if "****" in problem_statement:
            mark_code_left, mark_code_right = "****", "****"
        elif "***" in problem_statement:
            mark_code_left, mark_code_right = "***", "***"
        elif "**" in problem_statement:
            mark_code_left, mark_code_right = "**", "**"
        elif "*\n" in problem_statement:
            mark_code_left, mark_code_right = "*", "*"
        elif "####" in problem_statement:
            mark_code_left, mark_code_right = "#### ", ""
        elif "###" in problem_statement:
            mark_code_left, mark_code_right = "### ", ""
        elif "##" in problem_statement:
            mark_code_left, mark_code_right = "## ", ""
        elif "#\n" in problem_statement:
            mark_code_left, mark_code_right = "# ", ""
        else:
            mark_code_left, mark_code_right = "", ""

        reproduce_code_file_type = "JSX"

        # if this is Web UI, add the UI .md docs.
        if repo in [
            "alibaba-fusion/next",
            "carbon-design-system/carbon",
            "eslint/eslint",
            "grommet/grommet",
            "prettier/prettier",
            "quarto-dev/quarto-cli",
            "chartjs/Chart.js",
            "processing/p5.js",
        ]:
            problem_statement = f"""
{problem_statement.strip()}
\n
{mark_code_left}Reproduce Code:{mark_code_right}
```{reproduce_code_file_type}
{reproduce_code}
```
\n
{mark_code_left}Related Documents:{mark_code_right}
Here's some documents maybe are useful to understand Web Components. 
```markdown
{doc_files_content}
```
\n
"""
        elif repo in ["GoogleChrome/lighthouse"]:
            problem_statement = f"""
{problem_statement.strip()}
\n
{mark_code_left}Reproduce Code:{mark_code_right}
```json
{reproduce_code_dict}
```
"""

        else:
            problem_statement = f"""
{problem_statement.strip()}
\n
{mark_code_left}Reproduce Code:{mark_code_right}
```{reproduce_code_file_type}
{reproduce_code}
```
\n
"""

    # problem_statement = problem_statement.split("Related Documents:")[0]
    # logger.info(f'ISSUE Report:\n {problem_statement}')
    # logger.info(f'ISSUE Image:\n {image_file_list}')
    # return

    # 1.1 - get repo structure
    repo_structure_dict_file = os.path.join(args.output_dir, "1-1_repo_structure.json")
    if os.path.isfile(repo_structure_dict_file):
        logger.info(f"Repo Structure has existed (1): {repo_structure_dict_file}")
        repo_structure_dict = read_json_file(repo_structure_dict_file)
    elif (
        os.path.isfile(repo_structure_dict_file.replace("_Image2Code", ""))
        and os.path.isfile(repo_structure_dict_file) is False
    ):
        logger.info(
            f"Repo Structure has existed (2): {repo_structure_dict_file.replace('_Image2Code', '')}"
        )
        repo_structure_dict = read_json_file(
            repo_structure_dict_file.replace("_Image2Code", "")
        )
    elif (
        os.path.isfile(repo_structure_dict_file.replace(args.base_model + "/", ""))
        and os.path.isfile(repo_structure_dict_file) is False
    ):
        logger.info(
            f"Repo Structure has existed (3): {repo_structure_dict_file.replace(args.base_model + '/', '')}"
        )
        repo_structure_dict = read_json_file(
            repo_structure_dict_file.replace(args.base_model + "/", "")
        )
    elif (
        os.path.isfile(
            repo_structure_dict_file.replace(args.base_model + "/", "").replace(
                "_Image2Code", ""
            )
        )
        and os.path.isfile(repo_structure_dict_file) is False
    ):
        logger.info(
            f"Repo Structure has existed (4): {repo_structure_dict_file.replace(args.base_model + '/', '').replace('_Image2Code', '')}"
        )
        repo_structure_dict = read_json_file(
            repo_structure_dict_file.replace(args.base_model + "/", "").replace(
                "_Image2Code", ""
            )
        )
    else:
        try:
            clean_result = clean_repo(
                instance_repo_path, logger
            )  # clean the repo changes
            repo_structure_dict = create_structure(instance_repo_path, args)
            save_json_file(repo_structure_dict_file, repo_structure_dict)
        except:
            repo_structure_dict = {}
            logger.info("Repo Structure Parser Error!")
    repo_structure_filtering = show_project_structure(
        repo_structure_dict, args
    )  # Filtering non-js files
    logger.info(f"Repo Path: {instance_repo_path}")
    save_file(
        repo_structure_dict_file.replace(".json", ".txt"), repo_structure_filtering
    )
    # logger.info(f'Repo Structure:\n{repo_structure_filtering}')
    # return

    # 1.2 - find all bug files by looking repo structure
    # Action: input problem_statement and repo_structure to ask LLM infer related bug files
    bug_files_dict_file = os.path.join(args.output_dir, "1-2_bug_files.json")
    if os.path.isfile(bug_files_dict_file):
        logger.info(f"Bug Files has existed: {bug_files_dict_file}")
        bug_files_dict = read_json_file(bug_files_dict_file)
    else:
        system_prompt, user_prompt = all_file_locate_prompt_construction(
            repo_structure_filtering, problem_statement, image_file_list, args
        )
        if "gpt" in args.base_model or "o4-mini" in args.base_model:
            bug_files_dict, token_usage = openai_chat(
                system_prompt,
                user_prompt,
                args,
                args.all_bug_file_temperature,
                args.all_bug_file_samples,
            )
        elif "claude" in args.base_model:
            bug_files_dict, bug_files_str, token_usage = claude_chat(
                system_prompt,
                user_prompt,
                args,
                args.all_bug_file_temperature,
                args.all_bug_file_samples,
            )
            save_file(bug_files_dict_file.replace(".json", ".txt"), bug_files_str)
        save_json_file(bug_files_dict_file, bug_files_dict)
        token_usage_dict[bug_files_dict_file] = token_usage
    logger.info(f"Bug Files Created")
    # return

    # bug_files_agent = file_level_locating_agent(instance_id, instance_repo_path, instance_info, args)

    # check the file path and fix it
    bug_files_dict, all_files_list = check_bug_files_path(
        bug_files_dict, repo_structure_dict
    )
    # logger.info(all_files_list)
    save_json_file(
        os.path.join(args.output_dir, "1-3_bug_files_checked.json"), bug_files_dict
    )
    logger.info(f"Bug Files Checked")
    # return

    # find all bug files by searching keywords
    bug_files_dict_with_keyword_file = os.path.join(
        args.output_dir, "1-4_bug_files_with_keyword.json"
    )
    if args.keywords_searching == "True":
        if os.path.isfile(bug_files_dict_with_keyword_file) is False:
            # generate keyworkds form bug images and report
            system_prompt, user_prompt = keywords_generation_prompt_construction(
                problem_statement, image_file_list
            )
            bug_keywords_dict, token_usage = openai_chat(
                system_prompt,
                user_prompt,
                args,
                args.bug_keywords_temperature,
                args.bug_keywords_samples,
            )
            print(bug_keywords_dict)
            logger.info(
                f"🔍 Bug Keywords:\n {bug_keywords_dict[1]['bug_keywords']} ..."
            )

            # seaching files by using bug keywords
            logger.info(f"🔍 Search Bug Keywords in {instance_repo_path} ...")
            bug_keywords = bug_keywords_dict[1]["bug_keywords"]
            # bug_keywords = [
            #     "formatter", "format(", "highlight(", "shiki", "async", "await",
            #     "applyFixes", "bracketSpacing", "semi", "rules", "lintRules", "fixable"
            # ]
            bug_files_searching_keywords = bug_file_searching_by_keywords(
                instance_repo_path, all_files_list, bug_keywords
            )
            bug_keywords_dict[1]["bug_files"] = bug_files_searching_keywords
            save_json_file(bug_files_dict_with_keyword_file, bug_keywords_dict)
            logger.info(
                f"\n✅ Search Completed, Save Top-{len(bug_files_searching_keywords)} files."
            )
        else:
            bug_files_dict_with_keyword = read_json_file(
                bug_files_dict_with_keyword_file
            )
            bug_files_searching_keywords = bug_files_dict_with_keyword["1"]["bug_files"]

        bug_files_dict["1"]["bug_files"].extend(
            [bug_file[0] for bug_file in bug_files_searching_keywords]
        )
        save_json_file(
            bug_files_dict_with_keyword_file.replace("1-4_", "1-4-1_"), bug_files_dict
        )

    # logger.info(f'{bug_files_dict}')
    # return

    # need add RAG embedding
    bug_files_dict_with_RAG_file = os.path.join(
        args.output_dir, "1-4_bug_files_with_RAG.json"
    )
    if args.RAG_query == "True":
        if os.path.isfile(bug_files_dict_with_RAG_file) is False:
            first_key = next(iter(bug_files_dict))  # get the first key
            first_bug_file_list = bug_files_dict[first_key][
                "bug_files"
            ]  # get the bug_files
            No1_bug_file_path_list = []
            for first_bug_file in first_bug_file_list:
                No1_bug_file_path = os.path.dirname(
                    first_bug_file
                )  # Get the parent path
                if No1_bug_file_path not in No1_bug_file_path_list:
                    No1_bug_file_path_list.append(No1_bug_file_path)
            # No1_bug_file_path = os.path.dirname(bug_files_dict["1"]["bug_files"][0])  # Get the parent path
            # logger.info(f'No1_bug_file_path: {No1_bug_file_path}')
            # No1_bug_file_path_list = No1_bug_file_path_list[-1:]
            logger.info(f"RAG Dir Path: {No1_bug_file_path_list}")
            # return
            bug_files_rag_list = []

            bug_files_rag = query_bug_file(
                logger, instance_repo_path, No1_bug_file_path_list, 8, problem_statement
            )
            bug_files_rag_list.extend(bug_files_rag)
            logger.info(f"{bug_files_rag_list}")

            bug_files_dict[first_key]["bug_files"].extend(bug_files_rag_list)
            save_json_file(bug_files_dict_with_RAG_file, bug_files_dict)
        else:
            bug_files_dict = read_json_file(bug_files_dict_with_RAG_file)

    # return

    # 2.1 - compressing all bug files
    compressed_bug_files_dict_file = os.path.join(
        args.output_dir, "2-1_compressed_bug_files.json"
    )
    if os.path.isfile(compressed_bug_files_dict_file):
        logger.info(
            f"Compressed Bug Files has existed: {compressed_bug_files_dict_file}"
        )
        compressed_bug_files_dict = read_json_file(compressed_bug_files_dict_file)
    else:
        compressed_bug_files_dict = {}
        # bug_files_list = list(set(sum([bug_files_dict[key]['bug_files'] for key in bug_files_dict.keys()], [])))
        bug_files_list = list(
            dict.fromkeys(
                sum(
                    [bug_files_dict[key]["bug_files"] for key in bug_files_dict.keys()],
                    [],
                )
            )
        )

        for index, bug_file in enumerate(bug_files_list):
            bug_file_path = os.path.join(instance_repo_path, bug_file)
            # logger.info(f'{bug_file}')
            bug_file_structure_dict = get_bug_file_structure_dict(
                bug_file, repo_structure_dict
            )
            try:
                compressed_bug_file_content_list = compressing_javascript_file(
                    bug_file_structure_dict, save_variable_declaration=False
                )
            except:
                continue

            compressed_bug_files_dict[index + 1] = {}
            compressed_bug_files_dict[index + 1]["bug_file"] = bug_file
            if len(bug_file_structure_dict["text"]) > args.max_lines_per_key_file:
                compressed_bug_files_dict[index + 1]["compressed"] = "YES"
                compressed_bug_files_dict[index + 1]["line_numbers"] = len(
                    bug_file_structure_dict["text"]
                )
                compressed_bug_files_dict[index + 1]["compressed_line_numbers"] = len(
                    compressed_bug_file_content_list
                )
                compressed_bug_files_dict[index + 1]["compressed_bug_file_content"] = (
                    """""".join(compressed_bug_file_content_list)
                )
                if (
                    compressed_bug_files_dict[index + 1][
                        "compressed_bug_file_content"
                    ].strip()
                    == ""
                ):
                    compressed_bug_files_dict[index + 1]["compressed"] = "YES2NO"
                    compressed_bug_files_dict[index + 1][
                        "compressed_bug_file_content"
                    ] = "\n".join(bug_file_structure_dict["text"])

            else:
                compressed_bug_files_dict[index + 1]["compressed"] = "NO"
                compressed_bug_files_dict[index + 1]["line_numbers"] = len(
                    bug_file_structure_dict["text"]
                )
                compressed_bug_files_dict[index + 1]["compressed_line_numbers"] = len(
                    bug_file_structure_dict["text"]
                )
                compressed_bug_files_dict[index + 1]["compressed_bug_file_content"] = (
                    "\n".join(bug_file_structure_dict["text"])
                )

        save_json_file(compressed_bug_files_dict_file, compressed_bug_files_dict)
    logger.info(f"Compressed Bug Files: {compressed_bug_files_dict_file}")
    # return

    # 2.2 - find key bug files by looking compressed bug files
    # Action: input problem_statement and compressed bug files from step-2.1, then ask LLM to query key bug files
    key_bug_files_dict_file = os.path.join(args.output_dir, "2-2_key_bug_files.json")
    if os.path.isfile(key_bug_files_dict_file):
        logger.info(f"Key Bug Files has existed: {bug_files_dict_file}")
        key_bug_files_dict = read_json_file(key_bug_files_dict_file)
    else:
        # if candidate bug files is too much，LLM will filtering some files to get the key bug files
        if len(compressed_bug_files_dict.keys()) > args.max_candidate_bug_files:
            system_prompt, user_prompt = key_file_locate_prompt_construction(
                compressed_bug_files_dict,
                problem_statement,
                image_file_list,
                args.max_candidate_bug_files,
                args,
            )
            if "gpt" in args.base_model or "o4-mini" in args.base_model:
                key_bug_files_dict, token_usage = openai_chat(
                    system_prompt,
                    user_prompt,
                    args,
                    args.key_bug_file_temperature,
                    args.key_bug_file_samples,
                )
            if "claude" in args.base_model:
                key_bug_files_dict, key_bug_files_str, token_usage = claude_chat(
                    system_prompt,
                    user_prompt,
                    args,
                    args.key_bug_file_temperature,
                    args.key_bug_file_samples,
                )
                save_file(
                    key_bug_files_dict_file.replace(".json", ".txt"), key_bug_files_str
                )
            token_usage_dict[key_bug_files_dict_file] = token_usage
        else:
            key_bug_files_dict = {}
            key_bug_files_dict["1"] = {
                "bug_files": [
                    compressed_bug_files_dict[key]["bug_file"]
                    for key in compressed_bug_files_dict.keys()
                ]
            }
        save_json_file(key_bug_files_dict_file, key_bug_files_dict)
    logger.info(f"Key Bug Files: {key_bug_files_dict_file}")

    # check the key file path and fix it
    key_bug_files_dict, all_files_list = check_bug_files_path(
        key_bug_files_dict, repo_structure_dict
    )
    save_json_file(
        os.path.join(args.output_dir, "2-2_key_bug_files_checked.json"),
        key_bug_files_dict,
    )
    logger.info(f"Key Bug Files Checked")

    # 3.1 - compressing key bug files
    compressed_key_bug_files_dict_file = os.path.join(
        args.output_dir, "3-1_compressed_key_bug_files.json"
    )
    if os.path.isfile(compressed_key_bug_files_dict_file):
        logger.info(
            f"Compressed Key Bug Files has existed: {compressed_key_bug_files_dict_file}"
        )
        compressed_key_bug_files_dict = read_json_file(
            compressed_key_bug_files_dict_file
        )
    else:
        compressed_key_bug_files_dict = {}
        key_bug_files_list = sum(
            [key_bug_files_dict[key]["bug_files"] for key in key_bug_files_dict.keys()],
            [],
        )

        for index, bug_file in enumerate(key_bug_files_list):
            bug_file_path = os.path.join(instance_repo_path, bug_file)
            bug_file_structure_dict = get_bug_file_structure_dict(
                bug_file, repo_structure_dict
            )
            compressed_key_bug_file_content_list = compressing_javascript_file(
                bug_file_structure_dict, save_variable_declaration=False
            )

            compressed_key_bug_files_dict[index + 1] = {}
            compressed_key_bug_files_dict[index + 1]["bug_file"] = bug_file
            if len(bug_file_structure_dict["text"]) > args.max_lines_per_key_file:
                compressed_key_bug_files_dict[index + 1]["compressed"] = "YES"
                compressed_key_bug_files_dict[index + 1]["line_numbers"] = len(
                    bug_file_structure_dict["text"]
                )
                compressed_key_bug_files_dict[index + 1]["compressed_line_numbers"] = (
                    len(compressed_key_bug_file_content_list)
                )
                compressed_key_bug_files_dict[index + 1][
                    "compressed_bug_file_content"
                ] = """""".join(compressed_key_bug_file_content_list)
                if (
                    compressed_key_bug_files_dict[index + 1][
                        "compressed_bug_file_content"
                    ].strip()
                    == ""
                ):
                    compressed_key_bug_files_dict[index + 1]["compressed"] = "YES2NO"
                    compressed_key_bug_files_dict[index + 1][
                        "compressed_bug_file_content"
                    ] = "\n".join(bug_file_structure_dict["text"])
            else:
                compressed_key_bug_files_dict[index + 1]["compressed"] = "NO"
                compressed_key_bug_files_dict[index + 1]["line_numbers"] = len(
                    bug_file_structure_dict["text"]
                )
                compressed_key_bug_files_dict[index + 1]["compressed_line_numbers"] = (
                    len(bug_file_structure_dict["text"])
                )
                compressed_key_bug_files_dict[index + 1][
                    "compressed_bug_file_content"
                ] = "\n".join(bug_file_structure_dict["text"])

        save_json_file(
            compressed_key_bug_files_dict_file, compressed_key_bug_files_dict
        )
    logger.info(f"Compressed Key Bug Files: {compressed_key_bug_files_dict_file}")

    # 3.2 - locate all bug classes/functions
    # Action: input problem_statement and compressed key bug files from step-3.1, then ask LLM to find possible bug classes/functions
    key_bug_classes_functions_dict_file = os.path.join(
        args.output_dir, "3-2_key_bug_classes_functions.json"
    )
    if os.path.isfile(key_bug_classes_functions_dict_file):
        logger.info(
            f"Key Bug Classes/Functions File has existed: {key_bug_classes_functions_dict_file}"
        )
        key_bug_classes_functions_dict = read_json_file(
            key_bug_classes_functions_dict_file
        )
    else:
        if (
            len(problem_statement.split("\n")) > 1500
            and "Related Documents:" in problem_statement
        ):
            logger.info(
                "Too Much Docs Content, Please Remove before locating all bug classes/functions..."
            )
            problem_statement = problem_statement.split("Related Documents:")[0]
        system_prompt, user_prompt = key_class_function_locate_prompt_construction(
            compressed_key_bug_files_dict, problem_statement, image_file_list, args
        )
        if "p5.js" in repo:
            system_prompt = (
                system_prompt
                + """\n*Note that if function format is 'p5.RendererGL.prototype.newBuffers = function(gId, obj) {...}', the function name is 'p5.RendererGL.prototype.newBuffers'. Don't output incomplete function name."""
            )

        if "gpt" in args.base_model or "o4-mini" in args.base_model:
            key_bug_classes_functions_dict, token_usage = openai_chat(
                system_prompt,
                user_prompt,
                args,
                args.key_bug_class_function_temperature,
                args.key_bug_class_function_samples,
            )
        if "claude" in args.base_model:
            (
                key_bug_classes_functions_dict,
                key_bug_classes_functions_str,
                token_usage,
            ) = claude_chat(
                system_prompt,
                user_prompt,
                args,
                args.key_bug_class_function_temperature,
                args.key_bug_class_function_samples,
            )
            save_file(
                key_bug_classes_functions_dict_file.replace(".json", ".txt"),
                key_bug_classes_functions_str,
            )

        save_json_file(
            key_bug_classes_functions_dict_file, key_bug_classes_functions_dict
        )
        token_usage_dict[key_bug_classes_functions_dict_file] = token_usage
    logger.info(f"Key Bug Classes/Functions: {key_bug_classes_functions_dict_file}")
    # return

    # 4.1 - merge all bug classes/functions
    # Action: merge all classes and functions or elements
    merge_bug_classes_functions_dict_file = os.path.join(
        args.output_dir, "4-1_merged_key_bug_classes_functions.json"
    )

    merge_bug_classes_functions_dict = {}
    merge_bug_classes_functions_dict["bug_classes"] = list(
        dict.fromkeys(
            sum(
                [
                    key_bug_classes_functions_dict[key]["bug_classes"]
                    for key in key_bug_classes_functions_dict.keys()
                ],
                [],
            )
        )
    )
    merge_bug_classes_functions_dict["bug_functions"] = list(
        dict.fromkeys(
            sum(
                [
                    key_bug_classes_functions_dict[key]["bug_functions"]
                    for key in key_bug_classes_functions_dict.keys()
                ],
                [],
            )
        )
    )
    # note that p5.js Repo have some class definition in Function Comments, so LLM may extract func name as class name
    # here we add class names to func names to avoid incorre extraction
    if "p5.js" in repo:
        merge_bug_classes_functions_dict["bug_functions"].extend(
            merge_bug_classes_functions_dict["bug_classes"]
        )
    save_json_file(
        merge_bug_classes_functions_dict_file, merge_bug_classes_functions_dict
    )
    logger.info(
        f"Merged Bug Classes/Functions: {merge_bug_classes_functions_dict_file}"
    )
    # return

    # 4.2 - check all classes/functions to get the correct elements
    checked_bug_classed_functions_dict_file = os.path.join(
        args.output_dir, "4-2_checked_key_bug_classes_functions.json"
    )
    checked_bug_classed_functions_dict = {}
    checked_bug_classed_functions_dict["bug_classes"] = {}
    checked_bug_classed_functions_dict["bug_functions"] = {}
    key = 1

    for file_class in merge_bug_classes_functions_dict["bug_classes"]:
        try:
            if "//" in file_class:
                pass
            else:
                file_class = file_class + "// "
            bug_file_path = file_class.split("//")[0]
            bug_class_name = file_class.split("//")[1]
            if "." not in bug_file_path:
                continue

            bug_file_structure_dict = get_bug_file_structure_dict(
                bug_file_path, repo_structure_dict
            )
            checked_bug_classed_functions_dict["bug_classes"][key] = {}
            checked_bug_classed_functions_dict["bug_classes"][key]["class_name"] = (
                bug_class_name
            )
            checked_bug_classed_functions_dict["bug_classes"][key]["file_path"] = (
                bug_file_path
            )
            checked_bug_classed_functions_dict["bug_classes"][key]["class_details"] = [
                bug_class_dict
                for bug_class_dict in bug_file_structure_dict["classes"]
                if bug_class_dict["name"] == bug_class_name
            ]

            class_name_list = [
                bug_class_dict["name"]
                for bug_class_dict in bug_file_structure_dict["classes"]
            ]
            if (
                bug_class_name not in class_name_list
                and args.Checked_Exception == "True"
            ):
                if bug_class_name in "".join(bug_file_structure_dict["text"]):
                    logger.info(f"{bug_class_name} not in class_name_list")
                    checked_bug_classed_functions_dict["bug_classes"][key][
                        "class_name"
                    ] = bug_class_name + " (not found) "
                    if (
                        len(bug_file_structure_dict["text"])
                        <= args.max_lines_per_snippet
                    ):
                        checked_bug_classed_functions_dict["bug_classes"][key][
                            "class_details"
                        ].extend(
                            [
                                {
                                    "name": bug_class_name,
                                    "start_line": 1,
                                    "end_line": len(bug_file_structure_dict["text"]),
                                }
                            ]
                        )
                    else:
                        class_strat_line = 1
                        class_end_line = len(bug_file_structure_dict["text"])
                        for line_no, line_content in enumerate(
                            bug_file_structure_dict["text"]
                        ):
                            if bug_class_name in line_content:
                                class_strat_line = line_no + 1
                                break
                        if (
                            class_strat_line + args.max_lines_per_snippet
                            <= class_end_line
                        ):
                            class_end_line = (
                                class_strat_line + args.max_lines_per_snippet
                            )
                        else:
                            class_end_line = class_end_line
                        checked_bug_classed_functions_dict["bug_classes"][key][
                            "class_name"
                        ] = (
                            bug_class_name
                            + " (not found) "
                            + str(class_strat_line)
                            + "-"
                            + str(class_end_line)
                        )
                        checked_bug_classed_functions_dict["bug_classes"][key][
                            "class_details"
                        ].extend(
                            [
                                {
                                    "name": bug_class_name,
                                    "start_line": class_strat_line,
                                    "end_line": class_end_line,
                                }
                            ]
                        )

            if (
                checked_bug_classed_functions_dict["bug_classes"][key]["class_details"]
                == []
            ):
                del checked_bug_classed_functions_dict["bug_classes"][key]
            else:
                strat_line = checked_bug_classed_functions_dict["bug_classes"][key][
                    "class_details"
                ][0]["start_line"]
                end_line = checked_bug_classed_functions_dict["bug_classes"][key][
                    "class_details"
                ][0]["end_line"]
                checked_bug_classed_functions_dict["bug_classes"][key]["class_code"] = (
                    bug_file_structure_dict["text"][strat_line - 1 : end_line]
                )
                key += 1
        except Exception as e:
            del checked_bug_classed_functions_dict["bug_classes"][key]
            logger.info(f"{e}")

    for file_functions in merge_bug_classes_functions_dict["bug_functions"]:
        try:
            if "//" in file_functions:
                pass
            else:
                file_functions = file_functions + "// "
            bug_file_path = file_functions.split("//")[0]
            bug_functions_name = file_functions.split("//")[1]
            if len(file_functions.split("//")) > 2:
                bug_functions_name = file_functions.split("//")[-1]

            if "." not in bug_file_path:
                continue

            bug_file_structure_dict = get_bug_file_structure_dict(
                bug_file_path, repo_structure_dict
            )
            checked_bug_classed_functions_dict["bug_functions"][key] = {}
            checked_bug_classed_functions_dict["bug_functions"][key][
                "function_name"
            ] = bug_functions_name
            checked_bug_classed_functions_dict["bug_functions"][key]["file_path"] = (
                bug_file_path
            )
            checked_bug_classed_functions_dict["bug_functions"][key][
                "function_details"
            ] = [
                bug_functions_dict
                for bug_functions_dict in bug_file_structure_dict["functions"]
                if bug_functions_dict["name"] == bug_functions_name
            ]

            function_name_list = [
                bug_functions_dict["name"]
                for bug_functions_dict in bug_file_structure_dict["functions"]
            ]
            if (
                bug_functions_name not in function_name_list
                and args.Checked_Exception == "True"
            ):
                if bug_functions_name in "".join(bug_file_structure_dict["text"]):
                    logger.info(f"{bug_functions_name} not in function_name_list")
                    checked_bug_classed_functions_dict["bug_functions"][key][
                        "function_name"
                    ] = bug_functions_name + " (not found) "
                    if (
                        len(bug_file_structure_dict["text"])
                        <= args.max_lines_per_snippet
                    ):
                        checked_bug_classed_functions_dict["bug_functions"][key][
                            "function_details"
                        ].extend(
                            [
                                {
                                    "name": bug_functions_name,
                                    "start_line": 1,
                                    "end_line": len(bug_file_structure_dict["text"]),
                                }
                            ]
                        )
                    else:
                        function_strat_line = 1
                        function_end_line = len(bug_file_structure_dict["text"])
                        for line_no, line_content in enumerate(
                            bug_file_structure_dict["text"]
                        ):
                            if bug_functions_name in line_content:
                                function_strat_line = line_no + 1
                                break
                        if (
                            function_strat_line + args.max_lines_per_snippet
                            <= function_end_line
                        ):
                            function_end_line = (
                                function_strat_line + args.max_lines_per_snippet
                            )
                        else:
                            function_end_line = function_end_line
                        checked_bug_classed_functions_dict["bug_functions"][key][
                            "function_name"
                        ] = (
                            bug_functions_name
                            + " (not found) "
                            + str(function_strat_line)
                            + "-"
                            + str(function_end_line)
                        )
                        checked_bug_classed_functions_dict["bug_functions"][key][
                            "function_details"
                        ].extend(
                            [
                                {
                                    "name": bug_functions_name,
                                    "start_line": function_strat_line,
                                    "end_line": function_end_line,
                                }
                            ]
                        )

            if (
                checked_bug_classed_functions_dict["bug_functions"][key][
                    "function_details"
                ]
                == []
            ):
                del checked_bug_classed_functions_dict["bug_functions"][key]
            else:
                strat_line = checked_bug_classed_functions_dict["bug_functions"][key][
                    "function_details"
                ][0]["start_line"]
                end_line = checked_bug_classed_functions_dict["bug_functions"][key][
                    "function_details"
                ][0]["end_line"]
                checked_bug_classed_functions_dict["bug_functions"][key][
                    "function_code"
                ] = bug_file_structure_dict["text"][strat_line - 1 : end_line]
                key += 1
        except:
            pass

    save_json_file(
        checked_bug_classed_functions_dict_file, checked_bug_classed_functions_dict
    )
    # return

    # 4.3 - preprocess checked classes/functions to get the bug files with context_window
    bug_files_with_context_dict_file = os.path.join(
        args.output_dir, "4-3_checked_bug_files_with_context.json"
    )
    bug_files_with_context_dict = {}

    for key in checked_bug_classed_functions_dict["bug_classes"]:
        file_path = checked_bug_classed_functions_dict["bug_classes"][key]["file_path"]
        bug_file_structure_dict = get_bug_file_structure_dict(
            file_path, repo_structure_dict
        )
        bug_files_with_context_dict[file_path] = [
            "..." for i in bug_file_structure_dict["text"]
        ]
    for key in checked_bug_classed_functions_dict["bug_functions"]:
        file_path = checked_bug_classed_functions_dict["bug_functions"][key][
            "file_path"
        ]
        bug_file_structure_dict = get_bug_file_structure_dict(
            file_path, repo_structure_dict
        )
        bug_files_with_context_dict[file_path] = [
            "..." for i in bug_file_structure_dict["text"]
        ]

    for key in checked_bug_classed_functions_dict["bug_classes"].keys():
        class_name = checked_bug_classed_functions_dict["bug_classes"][key][
            "class_name"
        ]
        file_path = checked_bug_classed_functions_dict["bug_classes"][key]["file_path"]
        start_line = checked_bug_classed_functions_dict["bug_classes"][key][
            "class_details"
        ][0]["start_line"]
        end_line = checked_bug_classed_functions_dict["bug_classes"][key][
            "class_details"
        ][0]["end_line"]
        bug_file_structure_dict = get_bug_file_structure_dict(
            file_path, repo_structure_dict
        )
        bug_files_with_context_dict[file_path][
            start_line - args.context_window - 1 : end_line + args.context_window
        ] = bug_file_structure_dict["text"][
            start_line - args.context_window - 1 : end_line + args.context_window
        ]
    for key in checked_bug_classed_functions_dict["bug_functions"].keys():
        class_name = checked_bug_classed_functions_dict["bug_functions"][key][
            "function_name"
        ]
        file_path = checked_bug_classed_functions_dict["bug_functions"][key][
            "file_path"
        ]
        start_line = checked_bug_classed_functions_dict["bug_functions"][key][
            "function_details"
        ][0]["start_line"]
        end_line = checked_bug_classed_functions_dict["bug_functions"][key][
            "function_details"
        ][0]["end_line"]
        bug_file_structure_dict = get_bug_file_structure_dict(
            file_path, repo_structure_dict
        )
        bug_files_with_context_dict[file_path][
            start_line - args.context_window - 1 : end_line + args.context_window
        ] = bug_file_structure_dict["text"][
            start_line - args.context_window - 1 : end_line + args.context_window
        ]

    bug_files_with_context_dict = remove_blank_lines(
        bug_files_with_context_dict, blank_str="...", with_line_number=False
    )
    save_json_file(bug_files_with_context_dict_file, bug_files_with_context_dict)
    # return

    # save_json_file(bug_files_with_context_dict_file, bug_files_with_context_dict)

    # 4.4 - locate Top-N sets of line-level bug locations
    # not like agentless, we skip this step to locate the line/hunk level fault localization, we just use the class/function level fl like the SRepair

    # bug_files_with_context_line_level_fl_dict_file = os.path.join(args.output_dir, 'checked_bug_files_with_context_line_level_fl.json')
    # bug_files_with_context_line_level_fl_dict = {}
    # if os.path.isfile(bug_files_with_context_line_level_fl_dict_file):
    #     logger.info(f'bug_files_with_context_line_level_fl_dict_file has existed:\n{bug_files_with_context_line_level_fl_dict_file}')
    #     bug_files_with_context_line_level_fl_dict = read_json_file(bug_files_with_context_line_level_fl_dict_file)
    # else:
    #     system_prompt, user_prompt = line_level_class_function_locate_prompt_construction(bug_files_with_context_dict, problem_statement, image_file_list)
    #     bug_files_with_context_line_level_fl_dict = openai_chat(system_prompt, user_prompt, args, args.line_level_fl_temperature, args.line_level_fl_samples)
    #     save_json_file(bug_files_with_context_line_level_fl_dict_file, bug_files_with_context_line_level_fl_dict)
    # logger.info(f'Line-level FL Bug Classes/Functions:\n{bug_files_with_context_line_level_fl_dict_file}')

    # 5.1 - Patch Generation
    # Action: input problem_statement and bug_files_with_context from step-4.3, then ask LLM to generate patches
    if args.task == "run":
        patches_dict_file = os.path.join(args.output_dir, "5-1_patches.json")
    if args.task == "val":
        patches_dict_file = os.path.join(args.output_dir, "5-1_patches_val.json")

    if os.path.isfile(patches_dict_file):
        logger.info(f"Patches File has existed: {patches_dict_file}")
        patches_dict = read_json_file(patches_dict_file)
    else:
        for key in bug_files_with_context_dict.keys():
            bug_files_with_context_dict[key] = "\n".join(
                bug_files_with_context_dict[key]
            )

        # if len(problem_statement.split('\n')) > 1500 and "Related Documents:" in problem_statement
        if "Related Documents:" in problem_statement:
            problem_statement = problem_statement.split("Related Documents:")[0]
            logger.info("Remove docs before patch generation.")
            # logger.info(f'{problem_statement}')
        system_prompt, user_prompt = patch_generation_prompt_construction(
            bug_files_with_context_dict, problem_statement, image_file_list
        )
        if "gpt" in args.base_model or "o4-mini" in args.base_model:
            patches_dict, token_usage = openai_chat(
                system_prompt,
                user_prompt,
                args,
                args.patch_generation_temperature,
                args.patch_generation_samples,
            )
        if "claude" in args.base_model:
            patches_dict, patches_str, token_usage = claude_chat(
                system_prompt,
                user_prompt,
                args,
                args.patch_generation_temperature,
                args.patch_generation_samples,
            )
            save_file(patches_dict_file.replace(".json", ".txt"), patches_str)
        save_json_file(patches_dict_file, patches_dict)
        token_usage_dict[patches_dict_file] = token_usage
    # [save_file(os.path.join(args.output_dir, f'5-3-{index+1}_patches.md'), patches_dict[key]) for index, key in enumerate(patches_dict.keys())]

    # 5.2 - Patch Post-process
    patches_edits_dict = {}
    if args.task == "run":
        patches_edits_dict_file = os.path.join(
            args.output_dir, "5-2_patches_edits.json"
        )
    if args.task == "val":
        patches_edits_dict_file = os.path.join(
            args.output_dir, "5-2_patches_edits_val.json"
        )

    if os.path.isfile(patches_edits_dict_file):
        logger.info(f"Patches Edits File has existed: {patches_edits_dict_file}")
        patches_edits_dict = read_json_file(patches_edits_dict_file)
    else:
        for key in patches_dict.keys():
            patches_edits_dict[key] = extract_patch_edits(
                patches_dict[key], repo, check_pattern=""
            )
            if "prism" in repo or "highlightjs" in repo:
                first_num, second_num = float(key.split("/")[0]), int(key.split("/")[1])
                patches_edits_dict[f"{first_num + 0.1}/{second_num}"] = (
                    extract_patch_edits(patches_dict[key], repo, check_pattern="\n")
                )
                patches_edits_dict[f"{first_num + 0.2}/{second_num}"] = (
                    extract_patch_edits(patches_dict[key], repo, check_pattern="\\\\")
                )
                patches_edits_dict[f"{first_num + 0.3}/{second_num}"] = (
                    extract_patch_edits(patches_dict[key], repo, check_pattern="\\t")
                )
                patches_edits_dict[f"{first_num + 0.4}/{second_num}"] = (
                    extract_patch_edits(
                        patches_dict[key], repo, check_pattern="\\\\and\\t"
                    )
                )

        save_json_file(patches_edits_dict_file, patches_edits_dict)

    # 6.0 - Patch Check
    # Action: check the patch compilation error and refine it
    # patches_edits_dict_checked_file = os.path.join(args.output_dir, '5-2_patches_edits_checked.json')
    # if args.task == 'val' and args.Patch_Check == 'True':
    #     if os.path.isfile(patches_edits_dict_checked_file):
    #         logger.info(f'Patches Edits have checked: {patches_edits_dict_checked_file}')
    #         patches_edits_dict = read_json_file(patches_edits_dict_checked_file)
    #     else:
    #         logger.info(f'Check the compilation error in patches...')
    #         patches_edits_dict = patch_check(patches_edits_dict, instance_repo_path, repo_structure_dict, logger, args, bug_files_with_context_dict, problem_statement, image_file_list)

    # 6.1 - Patch Validation
    # Action：backfill the patches to bug repo，then reproduce the bug scenarion to check if solve the current bug or not
    plaus_patch_diff = patch_validation(
        patches_edits_dict, instance_repo_path, repo_structure_dict, logger, args
    )
    if args.task == "run":
        if plaus_patch_diff != "":
            save_file(os.path.join(args.output_dir, "changes.diff"), plaus_patch_diff)
        else:
            save_file(os.path.join(args.output_dir, "changes.diff"), plaus_patch_diff)
            logger.info("No Content in changes.diff")
    if args.task == "val":
        save_file(os.path.join(args.output_dir, "changes_val.diff"), plaus_patch_diff)

        if args.Patch_Select == "True" and int(args.val_patch_no) > 0:
            repair_feedback_dict, token_usage = repair_feedback(
                problem_statement, image_file_list, logger, args
            )
            save_json_file(
                os.path.join(args.output_dir, "5-3_feedback.json"), repair_feedback_dict
            )
            token_usage_dict[os.path.join(args.output_dir, "5-3_feedback.json")] = (
                token_usage
            )

    # save token usage
    token_usage_dict_file = os.path.join(args.output_dir, "token_usage.json")
    if os.path.isfile(token_usage_dict_file):
        pass
    else:
        save_json_file(token_usage_dict_file, token_usage_dict)


def repair_feedback(problem_statement, image_file_list, logger, args):
    repair_feedback_dict, token_usage = {}, 0
    bug_image_path = os.path.join(args.output_dir, "IMAGE", "0.png")
    fix_image_path = os.path.join(args.output_dir, "IMAGE", args.val_patch_no + ".png")

    # open bug and patch images
    bug_image = Image.open(bug_image_path).convert("RGB")
    fix_image = Image.open(fix_image_path).convert("RGB")

    # pixel-level matching
    if bug_image.size == fix_image.size:
        # comparing bug vs. patch images
        diff = ImageChops.difference(bug_image, fix_image)
        if diff.getbbox() is None:
            logger.info(
                f"Pixel-level matching successful, Patch_{args.val_patch_no} Fix fail"
            )
            repair_feedback_dict["final_answer"] = "NO"  # same
            return repair_feedback_dict, token_usage
        else:
            repair_feedback_dict = {}  # difference
    bug_image_list = get_bug_scenarion_images(bug_image_path, args)
    fix_image_list = get_bug_scenarion_images(fix_image_path, args)

    system_prompt, user_prompt = repair_feedback_prompt_construction(
        bug_image_list, fix_image_list, problem_statement, image_file_list
    )
    # logger.info(f'{user_prompt['bug_analyze']}')
    # logger.info(f'{user_prompt['fix_analyze']}')
    if "gpt" in args.base_model or "o4-mini" in args.base_model:
        repair_feedback_dict, token_usage = openai_chat(
            system_prompt,
            user_prompt,
            args,
            args.code_reproduce_temperature,
            args.code_reproduce_samples,
        )
    if "claude" in args.base_model:
        repair_feedback_dict, repair_feedback_str, token_usage = claude_chat(
            system_prompt,
            user_prompt,
            args,
            args.code_reproduce_temperature,
            args.code_reproduce_samples,
        )
    logger.info(f"{repair_feedback_dict}")
    if "yes" in repair_feedback_dict[1]["final_answer"].lower():
        logger.info(
            f"Patch_{args.val_patch_no} Repair_Feedback = {repair_feedback_dict[1]['final_answer']}, Resolved Issue"
        )
    else:
        logger.info(
            f"Patch_{args.val_patch_no} Repair_Feedback = {repair_feedback_dict[1]['final_answer']}, Fix Fail"
        )

    return repair_feedback_dict, token_usage


def patch_validation(
    patches_edits_dict, instance_repo_path, repo_structure_dict, logger, args
):
    for sample_no in patches_edits_dict.keys():
        if float(sample_no.split("/")[0]) >= float(args.val_patch_no):
            pass
        else:
            continue
        logger.info(f"Patch No. {sample_no}")

        # clean changed files
        clean_result = clean_repo(instance_repo_path, logger)
        # if 'chartjs__Chart.js-10806' in instance_repo_path or 'chartjs__Chart.js-11116' in instance_repo_path \
        #     or 'carbon-design-system' in instance_repo_path or 'PrismJS' in instance_repo_path:
        #     create_tmp_file = run_command(f'cd {instance_repo_path} && cd ../.. && mkdir -p tmp')
        #     clean_result = run_command(f'cd {instance_repo_path} && cp package.json ../../tmp/package.json && git reset --hard && cp ../../tmp/package.json ./package.json')
        #     logger.info(f'Do not Clean Repo Package.json')
        # elif 'openlayers' in instance_repo_path:
        #     create_tmp_file = run_command(f'cd {instance_repo_path} && cd ../.. && mkdir -p tmp')
        #     clean_result = run_command(f'cd {instance_repo_path} && cp config/tsconfig-build.json ../../tmp/tsconfig-build.json && git reset --hard && cp ../../tmp/tsconfig-build.json config/tsconfig-build.json')
        # else:
        #     clean_result = run_command(f'cd {instance_repo_path} && git reset --hard')
        #     logger.info(f'Repo Clean Result: {clean_result}')

        # backfill patch to repo
        patch_edits = patches_edits_dict[sample_no]
        # logger.info(f'{patch_edits}')

        # back_fill_patch(patch_edits, instance_repo_path, repo_structure_dict, logger)

        try:
            if float(args.val_patch_no) > 0:
                back_fill_patch(
                    patch_edits, instance_repo_path, repo_structure_dict, logger
                )
                logger.info(f"Pre Backfill Finish.")
            else:
                logger.info(f"Show bug scenarion, do not backfill.")
        except Exception as e:
            logger.info(f"Pre Backfill Fail: {e}")

        logger.info(instance_repo_path)

        # get patch diff
        get_patch_diff_result = run_command(
            f'cd {instance_repo_path} && git diff -- "*.js" "*.ts" "*.jsx" "*.tsx" "*.js.snap" "*.scss" "*.md" "*.lua"> changes.diff'
        )

        patch_diff = read_file(os.path.join(instance_repo_path, "changes.diff"))
        clean_patch_diff_result = run_command(
            f"cd {instance_repo_path} && rm changes.diff"
        )
        logger.info(f"Patch Diff Have Saved ... {get_patch_diff_result}")

        # check if generate available patch. Note that if we only reply the bug scenario (i.e., patch_no = 0), we will skip this check step
        if float(args.val_patch_no) > 0:
            if len(patch_diff.split("\n")) > 1:
                pass
            else:
                continue
        else:
            logger.info(f"Bug Reply...")
            pass

        # repo build
        if args.patch_generation_samples >= 1 and args.task == "val":
            build_cmd = make_build_cmd(instance_repo_path)
            build_response = "Fail"
            build_result = ""
            try:
                build_result = run_command(f"cd {instance_repo_path} && {build_cmd}")
                if "build" in build_cmd or "pack" in build_cmd:
                    logger.info(
                        f"Repo Build: {build_cmd} \n Build Result: \n{build_result}"
                    )
                    if (
                        "SyntaxError" in build_result
                        or "TypeError" in build_result
                        or "has Error" in build_result
                    ):
                        logger.info(
                            f"Repo Build Error: This patch has SyntaxError / TypeError / Error"
                        )
                        if "next" in instance_repo_path:
                            build_response = "Success"
                    elif "Local modules not found" in build_result:
                        logger.info(f"Please run npm/pnpm install")
                    elif "error Command failed with exit code 1" in build_result:
                        logger.info(
                            f"Repo Build Error: error Command failed with exit code 1"
                        )
                    else:
                        build_response = "Success"
                elif "test" in build_cmd:
                    logger.info(
                        f"Repo Test: {build_cmd} \n Test Result: \n{build_result}"
                    )
                    if "passing" in build_result:
                        build_response = "Success"
                    elif "mocha: not found" in build_result:
                        logger.info(f"Please run npm/pnpm install")
                    else:
                        logger.info(f"npm run test Error")
                elif "lint" in build_cmd:
                    logger.info(
                        f"Repo lint: {build_cmd} \n lint Result: \n{build_result}"
                    )
                    if "has Error" in build_result:
                        logger.info(f"Lint error")
                    else:
                        build_response = "Success"
                        logger.info(f"run lint Success")
                else:
                    build_response = "Success"
                    logger.info(f"No test or build, CMD: {build_cmd}")
            except Exception as e:
                logger.info(f"Repo Build/Test Error.")
        else:
            build_response = "NONE"
            logger.info(f"Repo Build No Need. Only 1 Patch.")

        logger.info(f"Wait {args.wait_time_after_build} S after REPO build/test...")
        time.sleep(int(args.wait_time_after_build))  # wait 20 seconds after fix

        if build_response == "Fail":
            logger.info(f"Current Patch No. {sample_no} Error, Run Next Patch...\n")
            # if line error, please try to refine this error patch
            continue
        else:
            if build_response == "NONE":
                logger.info(f"Repo Build No Need. Only 1 Patch. Skip This Step.")
            else:
                logger.info(
                    f"Current Patch No. {sample_no} Build/Test Success, finish build process.\n"
                )
            break

    # we should clean repo after validation
    # time.sleep(5)
    # run_command(f'cd {instance_repo_path} && git reset --hard')

    return patch_diff


def run_command(command, cwd=None):
    """Execute a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",  # Specify the encoding explicitly
        )
        if result.returncode != 0:
            # print(f"Run Command {command} has Error: {result.stderr} {result.stdout.strip()}")
            return f"Run Command {command} has Error: {result.stderr} {result.stdout.strip()}"
        return result.stdout.strip()
    except UnicodeDecodeError as e:
        print(f"Unicode decode error: {e}")
        return "Unicode decode error"


def clean_repo(instance_repo_path, logger):
    # clean changed files
    if (
        "chartjs__Chart.js-10806" in instance_repo_path
        or "chartjs__Chart.js-11116" in instance_repo_path
        or "carbon-design-system" in instance_repo_path
        or "PrismJS" in instance_repo_path
    ):
        create_tmp_file = run_command(
            f"cd {instance_repo_path} && cd ../.. && mkdir -p tmp"
        )
        clean_result = run_command(
            f"cd {instance_repo_path} && cp package.json ../../tmp/package.json && git reset --hard && cp ../../tmp/package.json ./package.json"
        )
        logger.info(f"Do not Clean Repo Package.json")
    elif "openlayers" in instance_repo_path:
        create_tmp_file = run_command(
            f"cd {instance_repo_path} && cd ../.. && mkdir -p tmp"
        )
        clean_result = run_command(
            f"cd {instance_repo_path} && cp config/tsconfig-build.json ../../tmp/tsconfig-build.json && git reset --hard && cp ../../tmp/tsconfig-build.json config/tsconfig-build.json"
        )
        logger.info(f"Do not Clean Repo config")
    else:
        clean_result = run_command(f"cd {instance_repo_path} && git reset --hard")
        logger.info(f"Repo Clean All Files")
    logger.info(f"Repo Clean Result: {clean_result}")
    return clean_result


def patch_check(
    patches_edits_dict,
    instance_repo_path,
    repo_structure_dict,
    logger,
    args,
    bug_files_with_context_dict,
    problem_statement,
    image_file_list,
):

    for sample_no in patches_edits_dict.keys():
        logger.info(f"Patch No. {sample_no}")

        # clean changed files

        if (
            "chartjs__Chart.js-10806" in instance_repo_path
            or "chartjs__Chart.js-11116" in instance_repo_path
            or "carbon-design-system" in instance_repo_path
            or "PrismJS" in instance_repo_path
        ):
            create_tmp_file = run_command(
                f"cd {instance_repo_path} && cd ../.. && mkdir -p tmp"
            )
            clean_result = run_command(
                f"cd {instance_repo_path} && cp package.json ../../tmp/package.json && git reset --hard && cp ../../tmp/package.json ./package.json"
            )
            logger.info(f"Do not Clean Repo Package.json")
        elif "openlayers" in instance_repo_path:
            create_tmp_file = run_command(
                f"cd {instance_repo_path} && cd ../.. && mkdir -p tmp"
            )
            clean_result = run_command(
                f"cd {instance_repo_path} && cp config/tsconfig-build.json ../../tmp/tsconfig-build.json && git reset --hard && cp ../../tmp/tsconfig-build.json config/tsconfig-build.json"
            )
        else:
            clean_result = run_command(f"cd {instance_repo_path} && git reset --hard")
            logger.info(f"Repo Clean Result: {clean_result}")

        # backfill patch to repo
        patch_edits = patches_edits_dict[sample_no]

        # back_fill_patch(patch_edits, instance_repo_path, repo_structure_dict, logger)

        try:
            if float(args.val_patch_no) > 0:
                back_fill_patch(
                    patch_edits, instance_repo_path, repo_structure_dict, logger
                )
                logger.info(f"Pre Backfill Finish.")
            else:
                logger.info(f"Show bug scenarion, do not backfill.")
        except Exception as e:
            logger.info(f"Pre Backfill Fail: {e}")

        logger.info(instance_repo_path)

        # get patch diff
        get_patch_diff_result = run_command(
            f'cd {instance_repo_path} && git diff -- "*.js" "*.ts" "*.jsx" "*.tsx" "*.js.snap" "*.scss" "*.md" "*.lua"> changes.diff'
        )
        if "scratchfoundation" in args.output_dir:
            get_patch_diff_result = run_command(
                f'cd {instance_repo_path} && git diff -- "*.js" "*.ts" "*.jsx" "*.tsx" "*.js.snap" "*.scss" "*.md" "*.lua" "*.json" > changes.diff'
            )
        patch_diff = read_file(os.path.join(instance_repo_path, "changes.diff"))
        clean_patch_diff_result = run_command(
            f"cd {instance_repo_path} && rm changes.diff"
        )
        logger.info(f"Patch Diff Have Saved ... {get_patch_diff_result}")

        # repo check
        if args.patch_generation_samples >= 1 and args.task == "val":
            build_cmd = make_check_cmd(instance_repo_path)
            build_response = "Fail"
            build_result = ""
            try:
                build_result = run_command(f"cd {instance_repo_path} && {build_cmd}")
                if "lint" in build_cmd:
                    logger.info(
                        f"Repo lint: {build_cmd} \n lint Result: \n{build_result}"
                    )
                    if "has Error" in build_result:
                        logger.info(f"Lint error")
                    else:
                        build_response = "Success"
                        logger.info(f"run lint Success")
            except Exception as e:
                logger.info(f"Repo Lint Error.")
        else:
            logger.info(f"Repo Lint No Need.")

        logger.info(f"Wait {args.wait_time_after_build} S after REPO lint...")
        time.sleep(int(args.wait_time_after_build))  # wait 20 seconds after fix

        if build_response == "Fail" and build_result != "":
            logger.info(
                f"Current Patch No. {sample_no} lint Error, Refine this Patch...\n"
            )
            # if lint error, ask the LLM to refine this error patch
            system_prompt, user_prompt = patch_check_prompt_construction(
                bug_files_with_context_dict, build_result, patch_edits
            )
            refined_patch_dict, token_usage = openai_chat(
                system_prompt, user_prompt, args, 0.0, 1
            )

            logger.info(f"{refined_patch_dict[1]}")
            refined_patch = json.loads(refined_patch_dict[1])

            patches_edits_dict[sample_no] = refined_patch

            logger.info(type(refined_patch))
            logger.info(f"{refined_patch}")

            break

            continue
        else:
            logger.info(
                f"Current Patch No. {sample_no} Lint Success, finish build process.\n"
            )
            continue

    # we should clean repo after validation
    # time.sleep(5)
    # run_command(f'cd {instance_repo_path} && git reset --hard')

    return patches_edits_dict
