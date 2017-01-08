#!/bin/bash

set -euo pipefail

DIR=$(dirname "$(readlink -f "$0")")

function parse_gcc_info()
{
    local version=$1
    local target_dir=$2
    shift 2
    local input_files=("$@")
    "$DIR"/parse-gcc-warning-options.py "${input_files[@]}" \
          > "$target_dir"/warnings-gcc-"$version".txt
    "$DIR"/parse-gcc-warning-options.py --unique "${input_files[@]}" \
          > "$target_dir"/warnings-gcc-unique-"$version".txt
    "$DIR"/parse-gcc-warning-options.py --top-level "${input_files[@]}" \
          > "$target_dir"/warnings-gcc-top-level-"$version".txt
}

GIT_DIR=$1

target_dir=$DIR/../gcc

git -C "$GIT_DIR" checkout gcc-3_4_6-release
parse_gcc_info 3.4 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_0_4-release
parse_gcc_info 4.0 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_1_2-release
parse_gcc_info 4.1 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_2_4-release
parse_gcc_info 4.2 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_3_6-release
parse_gcc_info 4.3 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_4_7-release
parse_gcc_info 4.4 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_5_4-release
parse_gcc_info 4.5 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c.opt}

git -C "$GIT_DIR" checkout gcc-4_6_4-release
parse_gcc_info 4.6 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

git -C "$GIT_DIR" checkout gcc-4_7_4-release
parse_gcc_info 4.7 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

git -C "$GIT_DIR" checkout gcc-4_8_5-release
parse_gcc_info 4.8 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

git -C "$GIT_DIR" checkout gcc-4_9_4-release
parse_gcc_info 4.9 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

git -C "$GIT_DIR" checkout gcc-5_4_0-release
parse_gcc_info 5 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

git -C "$GIT_DIR" checkout gcc-6_3_0-release
parse_gcc_info 6 "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

git -C "$GIT_DIR" fetch origin master
git -C "$GIT_DIR" checkout origin/master
parse_gcc_info NEXT "$target_dir" "$GIT_DIR"/gcc/{common.opt,c-family/c.opt}

versions=(
    3.4
    4.0
    4.1
    4.2
    4.3
    4.4
    4.5
    4.6
    4.7
    4.8
    4.9
    5
    6
    NEXT
)

seq 2 "${#versions[@]}" | while read -r current_version in ; do
    current=${versions[$(( current_version - 2 ))]}
    next=${versions[$(( current_version - 1 ))]}
    "$DIR"/create-diff.sh \
          "$target_dir"/warnings-gcc-unique-"$current".txt \
          "$target_dir"/warnings-gcc-unique-"$next".txt \
          > "$target_dir"/warnings-gcc-diff-"$current-$next".txt
done
