# GitHub Workflow Agent Instructions

## 1. Scope
Applies to `.github`. Read the root `AGENTS.md` first.

## 2. Responsibility
This path owns CI workflows, issue and PR templates and CODEOWNERS.

## 3. Allowed Changes
M1 coordinates workflow changes; each owner may request path-specific jobs.

## 4. Prohibited Changes
Do not weaken required checks, expose secrets or grant broad write permissions.

## 5. Contracts
CI calls the same Make targets used locally. Pin actions and use minimum permissions.

## 6. Required Tests
Validate workflow syntax and run the underlying local Make target before merge.

## 7. Completion
Required checks cover Python, Contract, generated Schema, integration and secret scanning.

## 8. Handoff
Workflow requests include job, command, trigger, required secret and failure policy.
