#!/usr/bin/env bash

set -euo pipefail

project_path="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

if [[ ! -d "${project_path}" ]]; then
  echo "Project path does not exist: ${project_path}"
  exit 1
fi

errors=0
warnings=0

pass() {
  echo "PASS: $1"
}

warn() {
  echo "WARN: $1"
  warnings=$((warnings + 1))
}

fail() {
  echo "FAIL: $1"
  errors=$((errors + 1))
}

require_file() {
  local rel_path="$1"
  if [[ -f "${project_path}/${rel_path}" ]]; then
    pass "Found ${rel_path}"
  else
    fail "Missing required file ${rel_path}"
  fi
}

require_file "README.md"
require_file "START_HERE.md"
require_file "project-control.yaml"
require_file "docs/architecture.md"
require_file "docs/current-build-pathway.md"
require_file "docs/manual.md"
require_file "docs/roadmap.md"
require_file "docs/policy/durable-development-engineering-policy.md"
require_file "docs/standards/README.md"
require_file "docs/standards/engineering-governance-by-use-case.md"
require_file "docs/standards/ship-ready-engineering-standard.md"
require_file "docs/risks/risk-register.md"

if [[ -f "${project_path}/project-control.yaml" ]]; then
  if grep -Eq '^project_name:' "${project_path}/project-control.yaml"; then
    pass "project-control.yaml includes project_name"
  else
    fail "project-control.yaml is missing project_name"
  fi

  if grep -Eq '^project_type:' "${project_path}/project-control.yaml"; then
    pass "project-control.yaml includes project_type"
  else
    fail "project-control.yaml is missing project_type"
  fi

  if grep -Eq '^use_case:' "${project_path}/project-control.yaml" && grep -Eq '^[[:space:]]+primary:[[:space:]]+[^[:space:]]' "${project_path}/project-control.yaml"; then
    pass "project-control.yaml includes use_case.primary"
  else
    warn "project-control.yaml is missing use_case.primary classification"
  fi

  if grep -Eq '^risk_tier: (low|medium|high|critical)$' "${project_path}/project-control.yaml"; then
    pass "project-control.yaml includes a valid risk_tier"
  else
    fail "project-control.yaml has a missing or invalid risk_tier"
  fi

  if grep -Eq '^governance_level: [0-4]$' "${project_path}/project-control.yaml"; then
    pass "project-control.yaml includes a valid governance_level"
  elif grep -Eq '^governance_level:' "${project_path}/project-control.yaml"; then
    fail "project-control.yaml has an invalid governance_level"
  else
    warn "project-control.yaml is missing governance_level"
  fi

  if grep -Eq '^repository_model: (single-repo|monorepo)$' "${project_path}/project-control.yaml"; then
    pass "project-control.yaml includes a valid repository_model"
  else
    fail "project-control.yaml has a missing or invalid repository_model"
  fi

  if grep -Eq '^project_type: agent$' "${project_path}/project-control.yaml"; then
    require_file "docs/agent-inventory.md"
    require_file "docs/model-registry.md"
    require_file "docs/prompt-register.md"
    require_file "docs/tool-permission-matrix.md"
  fi

  if grep -Eq '^project_type: documentation$' "${project_path}/project-control.yaml"; then
    warn "Documentation project detected, deploy/runbook checks are not required"
  else
    if [[ -f "${project_path}/docs/deployment-guide.md" ]]; then
      pass "Found docs/deployment-guide.md"
    else
      warn "Missing docs/deployment-guide.md"
    fi

    if [[ -f "${project_path}/docs/runbook.md" ]]; then
      pass "Found docs/runbook.md"
    else
      warn "Missing docs/runbook.md"
    fi
  fi
fi

if [[ -f "${project_path}/AGENTS.md" ]]; then
  pass "Found AGENTS.md"
else
  warn "Missing AGENTS.md"
fi

if [[ -d "${project_path}/scripts" ]]; then
  pass "Found scripts directory"
else
  warn "Missing scripts directory"
fi

if [[ ${errors} -gt 0 ]]; then
  echo
  echo "Governance check failed with ${errors} error(s) and ${warnings} warning(s)."
  exit 1
fi

echo
echo "Governance check passed with ${warnings} warning(s)."
