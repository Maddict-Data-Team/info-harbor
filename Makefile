.DEFAULT_GOAL := help

SHELL := /bin/bash
PYTHON ?= python3

# Allow "make custom 165" by capturing extra goals after the target
ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
CODE ?= $(firstword $(ARGS))

# Prevent Make from trying to build extra args like "165" as targets
$(foreach a,$(ARGS),$(eval $(a):;@:))

.PHONY: help custom custom-codename

help:
	@echo ""
	@echo "Makefile commands:"
	@echo "  make custom <int>                 Run custom_codename with positional code"
	@echo "  make custom-codename CODE=<int>   Run custom_codename with named code"
	@echo ""

custom:
	@[ -n "$(CODE)" ] || (echo "ERROR: CODE is required. Usage: make custom <int>"; exit 1)
	@echo "Running custom_codename with CODE=$(CODE)"
	@$(PYTHON) projects/automation/custom_codename.py $(CODE)

custom-codename: custom