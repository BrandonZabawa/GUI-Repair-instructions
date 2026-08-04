import argparse
import json
import logging
import os
from typing import cast

#from Code.workflow import file_level_locating_val
from workflow import file_level_locating_val
from datasets import Dataset, load_dataset

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--task", type=str, default="run")

    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--output_file", type=str, default="loc_outputs.jsonl")
    parser.add_argument("--log_file", type=str, default="loc_outputs.log")

    parser.add_argument("--base_model", type=str, default="gpt-4o-mini-2024-07-18")
    parser.add_argument("--top_n", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--num_samples", type=int, default=1)
    parser.add_argument("--all_bug_file_temperature", type=float, default=0.7)
    parser.add_argument("--all_bug_file_samples", type=int, default=2)
    parser.add_argument("--max_candidate_bug_files", type=int, default=4)
    parser.add_argument("--key_bug_file_temperature", type=float, default=0.0)
    parser.add_argument("--key_bug_file_samples", type=int, default=1)
    parser.add_argument("--key_bug_class_function_temperature", type=float, default=0.0)
    parser.add_argument("--key_bug_class_function_samples", type=int, default=1)
    parser.add_argument("--line_level_fl_temperature", type=float, default=0.0)
    parser.add_argument("--line_level_fl_samples", type=int, default=1)
    parser.add_argument("--patch_generation_temperature", type=float, default=0.0)
    parser.add_argument("--patch_generation_samples", type=int, default=1)

    parser.add_argument("--bug_keywords_temperature", type=float, default=0.0)
    parser.add_argument("--bug_keywords_samples", type=int, default=1)

    parser.add_argument("--bug_docs_temperature", type=float, default=0.0)
    parser.add_argument("--bug_docs_samples", type=int, default=1)

    parser.add_argument("--max_candidate_doc_files", type=int, default=6)

    parser.add_argument("--code_reproduce_temperature", type=float, default=0.0)
    parser.add_argument("--code_reproduce_samples", type=int, default=1)

    parser.add_argument("--openai_api_key", type=str, default="")

    parser.add_argument("--compress_assign", action="store_true")
    parser.add_argument("--compress_assign_total_lines", type=int, default=30)
    parser.add_argument("--compress_assign_prefix_lines", type=int, default=10)
    parser.add_argument("--compress_assign_suffix_lines", type=int, default=10)
    parser.add_argument("--context_window", type=int, default=10)

    parser.add_argument("--max_lines_per_snippet", type=int, default=500)
    parser.add_argument("--max_lines_per_key_file", type=int, default=500)

    parser.add_argument("--wait_time_after_build", type=int, default=0)
    parser.add_argument("--wait_time_after_api_request", type=int, default=20)
    parser.add_argument("--val_patch_no", type=str, default="1")

    parser.add_argument("--keywords_searching", default=False)
    parser.add_argument("--doc_RAG_query", default=False)
    parser.add_argument("--RAG_query", default=False)
    parser.add_argument("--Checked_Exception", default=False)

    parser.add_argument("--Patch_Check", default=False)
    parser.add_argument("--Patch_Select", default=False)
    parser.add_argument("--Code_Reply", default=False)
    parser.add_argument("--File_Sort", default=False)

    # dataset info
    parser.add_argument(
        "--dataset", type=str, default="princeton-nlp/SWE-bench_Multimodal"
    )
    parser.add_argument("--dataset_split", type=str, default="dev")
    parser.add_argument("--instance_id", type=str, default="chartjs__Chart.js-8868")
    parser.add_argument(
        "--repo_path", type=str, default="SWE-Bench-MM/Reproduce_Scenario"
    )

    parser.add_argument(
        "--mock", action="store_true", help="Mock run to compute prompt tokens."
    )

    return parser.parse_args()


def read_json_file(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def save_json_file(file_path, data):
    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)


def get_dataset():

    dataset_dict = {}
    dataset_json_file_path = os.path.join(
        "dataset", args.dataset_split, (args.dataset).split("/")[1] + ".json"
    )
    if not os.path.exists(os.path.join("dataset", args.dataset_split)):
        os.makedirs(os.path.join("dataset", args.dataset_split))

    if os.path.isfile(dataset_json_file_path):
        dataset_dict = read_json_file(dataset_json_file_path)
    else:
        dataset = cast(Dataset, load_dataset(args.dataset, split=args.dataset_split))
        for instance in dataset:
            instance_id = instance["instance_id"]
            dataset_dict[instance_id] = instance
        save_json_file(dataset_json_file_path, dataset_dict)

    return dataset_dict


def fault_localization_process(instance_id, instance_info):
    repo = instance_info["repo"]
    instance_repo_path = os.path.join(
        args.repo_path,
        args.dataset_split,
        instance_id.split("__")[0],
        instance_id,
        "REPO",
        repo.split("/")[-1],
    )
    if os.path.exists(instance_repo_path):
        logger.info(f"Open Instance Repo {repo} Path: {instance_repo_path}")
    else:
        logger.info(
            f"Instance Repo {repo} Path is not exist: {instance_repo_path}, Plese checkout repo"
        )
        return False

    # logger.info(f"")

    # root_output_dir = deep
    args.output_dir = os.path.join(
        original_output_dir, args.dataset_split, instance_id.split("__")[0], instance_id
    )

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    diff_file = os.path.join(args.output_dir, "changes.diff")
    if args.task == "run" and args.Code_Reply == "False":
        if os.path.isfile(diff_file):
            pass
        else:
            located_bug_files_result = file_level_locating_val(
                instance_id, instance_repo_path, instance_info, args, logger
            )
    elif args.task == "run" and args.Code_Reply == "True":
        if os.path.isfile(diff_file):
            pass
        else:
            located_bug_files_result = file_level_locating_val(
                instance_id, instance_repo_path, instance_info, args, logger
            )
    elif args.task == "val":
        located_bug_files_result = file_level_locating_val(
            instance_id, instance_repo_path, instance_info, args, logger
        )

    else:
        if os.path.isfile(diff_file):
            pass
        else:
            located_bug_files_result = file_level_locating_val(
                instance_id, instance_repo_path, instance_info, args, logger
            )


def main():
    dataset_dict = get_dataset()

    if args.openai_api_key == "":
        logger.info("Please set your API Key")
        return

    # fix a instance
    if (
        args.instance_id is not None
        and args.instance_id in dataset_dict.keys()
        and "__" in args.instance_id
    ):
        logger.info(f"Repair one instance ID...")
        logger.info(f"Repair Instance ID: {args.instance_id}")
        fault_localization_process(args.instance_id, dataset_dict[args.instance_id])
    # fix all instances in a project
    elif "__" not in args.instance_id and args.instance_id != "ALL":
        instances_num = 0
        instances_count = len(
            [
                instance_id
                for instance_id in dataset_dict.keys()
                if args.instance_id in instance_id
            ]
        )
        for instance_id in dataset_dict.keys():
            if args.instance_id in instance_id:
                instances_num += 1
                logger.info(f"")
                logger.info(f"================ {instance_id} ================")
                logger.info(f"")
                logger.info(
                    f"Instance No: {instances_num}/{instances_count}, ID: {instance_id}"
                )
                fault_localization_process(instance_id, dataset_dict[instance_id])

    # fix all instances
    elif args.instance_id == "ALL":
        logger.info(f"Repair all instances...")
        for instance_id in dataset_dict.keys():
            logger.info(f"Repair Instance ID: {instance_id}")
            fault_localization_process(instance_id, dataset_dict[instance_id])

    else:
        logger.info(f"Please give the correct instance ID")


if __name__ == "__main__":
    args = get_args()
    logger.info(args)
    # API KEY
    args.openai_api_key = ""
    args.claude_api_key = ""

    original_output_dir = args.output_dir
    main()
