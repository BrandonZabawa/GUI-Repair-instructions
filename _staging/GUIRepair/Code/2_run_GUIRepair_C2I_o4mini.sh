task=val                               # please set run/val. run: generate fix； val: validate fix
output_file=result.json                # save fault localization result to this file
log_file=repair_$task.log              # save log to this file
base_model=o4-mini-2025-04-16          # gpt-4o-2024-08-06 or gpt-4.1-2025-04-14 or claude-3-5-sonnet-20240620 
output_dir=$base_model/result
dataset=princeton-nlp/SWE-bench_Multimodal
dataset_split=test
val_patch_no=1                          # you can select the patch index 1-n to val the fix result. you can set 0 to replay the bug scenario
instance_id=highlightjs__highlight.js-3070          # you need to set "ALL" or only one id e.g.,"chartjs__Chart.js-8868" or only the Repo ID "chartjs"
repo_path=/Data/SWE-Bench-MM/Reproduce_Scenario
RAG_query=False                # True: open RAG; False: False: close RAG
Checked_Exception=True         # True: open the exception to save un-checked function/class; False: close ...
max_lines_per_snippet=500      # The context window of the Exception Func/Class
context_window=0
all_bug_file_temperature=1          # 0.7
all_bug_file_samples=2              # 2
max_candidate_bug_files=4           # 4
key_bug_file_temperature=0.0             # 0.0
key_bug_file_samples=1                   # 1
max_lines_per_key_file=500               # The context window of the key bug file 
key_bug_class_function_temperature=1     # 0.7
key_bug_class_function_samples=2         # 4
line_level_fl_temperature=0.9
line_level_fl_samples=40
patch_generation_temperature=1     # 0.8
patch_generation_samples=20
wait_time_after_api_request=0      # please set 0s if your api no request limit
wait_time_after_build=0            # you need leave some time to check bug scenario

mkdir -p $output_dir

if [[ "$instance_id" == *"__"* ]]; then
    instance_prefix=$(echo $instance_id | awk -F'__' '{print $1}')
    log_file_path=$output_dir/$dataset_split/$instance_prefix/$instance_id
else
    log_file_path=$output_dir/$dataset_split/$instance_id
fi

mkdir -p $log_file_path


python main.py \
    --task $task\
    --output_dir $output_dir\
    --output_file $output_file\
    --base_model $base_model\
    --dataset $dataset\
    --dataset_split $dataset_split\
    --instance_id $instance_id\
    --repo_path $repo_path\
    --RAG_query $RAG_query\
    --Checked_Exception $Checked_Exception\
    --max_lines_per_snippet $max_lines_per_snippet\
    --context_window $context_window\
    --all_bug_file_temperature $all_bug_file_temperature\
    --all_bug_file_samples $all_bug_file_samples\
    --max_candidate_bug_files $max_candidate_bug_files\
    --key_bug_file_temperature $key_bug_file_temperature\
    --key_bug_file_samples $key_bug_file_samples\
    --key_bug_class_function_temperature $key_bug_class_function_temperature\
    --key_bug_class_function_samples $key_bug_class_function_samples\
    --line_level_fl_temperature $line_level_fl_temperature\
    --line_level_fl_samples $line_level_fl_samples\
    --patch_generation_temperature $patch_generation_temperature\
    --patch_generation_samples $patch_generation_samples\
    --wait_time_after_api_request $wait_time_after_api_request\
    --wait_time_after_build $wait_time_after_build\
    --val_patch_no $val_patch_no\
    2>&1 | tee $log_file_path/$log_file

