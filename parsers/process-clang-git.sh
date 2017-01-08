#!/bin/bash

set -euo pipefail

DIR=$(dirname "$(readlink -f "$0")")

function parse_clang_info()
{
    local version=$1
    local target_dir=$2
    shift 2
    local input_files=("$@")
    "$DIR"/parse-clang-diagnostic-groups.py "${input_files[@]}" \
          > "$target_dir"/warnings-clang-"$version".txt
    "$DIR"/parse-clang-diagnostic-groups.py --unique "${input_files[@]}" \
          > "$target_dir"/warnings-clang-unique-"$version".txt
    "$DIR"/parse-clang-diagnostic-groups.py --top-level "${input_files[@]}" \
          > "$target_dir"/warnings-clang-top-level-"$version".txt
}

GIT_DIR=$1

target_dir=$DIR/../clang

git -C "$GIT_DIR" checkout origin/release_32
parse_clang_info 3.2 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_33
parse_clang_info 3.3 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_34
parse_clang_info 3.4 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_35
parse_clang_info 3.5 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_36
parse_clang_info 3.6 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_37
parse_clang_info 3.7 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_38
parse_clang_info 3.8 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" checkout origin/release_39
parse_clang_info 3.9 "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

git -C "$GIT_DIR" fetch origin master
git -C "$GIT_DIR" checkout origin/master
parse_clang_info NEXT "$target_dir" "$GIT_DIR"/include/clang/Basic/DiagnosticGroups.td

versions=(
    3.2
    3.3
    3.4
    3.5
    3.6
    3.7
    3.8
    3.9
    NEXT
)

seq 2 "${#versions[@]}" | while read -r current_version in ; do
    current=${versions[$(( current_version - 2 ))]}
    next=${versions[$(( current_version - 1 ))]}
    "$DIR"/create-diff.sh \
          "$target_dir"/warnings-clang-unique-"$current".txt \
          "$target_dir"/warnings-clang-unique-"$next".txt \
          > "$target_dir"/warnings-clang-diff-"$current-$next".txt
done
