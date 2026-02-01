---
name: ucas-dev
description: "Development tools and skills for UCAS system development"
---

# UCAS Development Skills

This directory contains skills specifically for developing the UCAS system itself.

## Purpose

The `ucas` mod is a project-specific mod that provides development tools and skills for working on the UCAS codebase. It is automatically included when running agents within the UCAS project.

## Adding Skills

To add a new skill for UCAS development:

1. Create a new directory in this folder: `./skills/skill-name/`
2. Add a `SKILL.md` file with the skill definition
3. The skill will be automatically available to all agents running in this project

## Example Skills

Future skills might include:
- Python testing utilities
- YAML validation tools
- Documentation generation helpers
- Code analysis tools
