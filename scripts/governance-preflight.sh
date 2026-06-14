#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${repo_root}/automation/governance_check.sh" ]]; then
  bash "${repo_root}/automation/governance_check.sh" "${repo_root}"
elif [[ -f "${script_dir}/governance-check.sh" ]]; then
  bash "${script_dir}/governance-check.sh" "${repo_root}"
elif [[ -n "${GOVERNANCE_HOME:-}" && -f "${GOVERNANCE_HOME}/automation/governance_check.sh" ]]; then
  bash "${GOVERNANCE_HOME}/automation/governance_check.sh" "${repo_root}"
else
  echo "No governance checker is available for this repository."
  echo "Expected one of:"
  echo "  - ${repo_root}/automation/governance_check.sh"
  echo "  - ${script_dir}/governance-check.sh"
  echo "  - \$GOVERNANCE_HOME/automation/governance_check.sh"
  exit 1
fi
