#!/usr/bin/env bash

env_file_vars=(
  "${!LD_@}"
  "${!OIDC_@}"
  TZ_FILE
  HOST_NAME_FILE
)

load_env_files() {
  local file_var var value
  local file_vars=("$@")
  if (( $# == 0 )); then
    file_vars=("${env_file_vars[@]}")
  fi

  for file_var in "${file_vars[@]}"; do
    [[ "$file_var" == *_FILE && -n "${!file_var:-}" ]] || continue

    var="${file_var%_FILE}"
    if ! value=$(cat -- "${!file_var}"); then
      printf 'Could not read %s\n' "$file_var" >&2
      return 1
    fi

    export "$var=$value"
    unset "$file_var"
  done
}
