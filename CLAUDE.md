# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-assisted GitHub Issue automation project. The main script (`ai-bot/run_issue.py`) automates the workflow of:
1. Fetching assigned GitHub Issues
2. Generating implementation plans via Claude Code
3. Creating feature branches
4. Implementing code changes
5. Running tests and creating PRs

## Commands

### Run the main automation script
```bash
python ai-bot/run_issue.py [ISSUE_ID]
```
- Without arguments: automatically fetches issues assigned to the current user
- With ISSUE_ID: processes the specific issue

### Run tests
```bash
pytest
```

## Code Architecture

- `ai-bot/run_issue.py` - Main entry point that orchestrates the entire workflow using GitHub CLI (`gh`) for API operations and invoking Claude Code for AI assistance

## Dependencies

- GitHub CLI (`gh`) - Required for issue/PR operations
- Python 3.x with `pytest` for testing
