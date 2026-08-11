SRC_DIR  := src
PKG      := fly_in
TEST_DIR := tests
DOCS_DIR := docs/
DATA_DIR := data
VENDOR_DIR := vendor

# the map used by the run/debug targets
# (override with: make run MAP=data/maps/hard/01_maze_nightmare.txt)
MAP ?= $(DATA_DIR)/maps/easy/01_linear_path.txt

# everything the linters look at
LINT_PATHS := $(SRC_DIR) $(TEST_DIR)

MYPY_FLAGS := --warn-return-any --warn-unused-ignores --ignore-missing-imports \
              --disallow-untyped-defs --check-untyped-defs

# turn-in packaging
NAME      := fly-in
TAG       ?= v1.0.0
DIST_DIR  := dist
STAGE_DIR := $(DIST_DIR)/$(NAME)_turnin
TURNIN    := $(DIST_DIR)/$(NAME)_turnin_$(TAG).tar.gz

.PHONY: install run debug \
        ruff flake8 mypy mypy-strict \
        lint lint-strict lint-all \
        test test-turnin test-all \
        require-tag stage dist tag publish \
        clean fclean

# install project dependencies
install:
	uv sync

# run the simulator on a map (override with: make run MAP=<path>)
run:
	uv run python -m $(PKG) $(MAP)

# run the simulator under the pdb debugger
debug:
	uv run python -m pdb -m $(PKG) $(MAP)

# mypy with the subject's mandatory flags
mypy:
	uv run mypy $(MYPY_FLAGS) $(LINT_PATHS)

# mypy in strict mode
mypy-strict:
	uv run mypy --strict $(LINT_PATHS)

# flake8 (the subject's required style checker; run ephemerally via uvx)
flake8:
	uvx flake8 $(LINT_PATHS)

# ruff linter
# (more throrough than flake8,
# and I (lrain) need it for my code editor anyway,
# so i might as well include optionally)
ruff:
	uv run ruff check $(LINT_PATHS)

# subject's mandatory lint rule
lint: flake8 mypy

# subject's optional lint rule: flake8 + mypy --strict
lint-strict: flake8 mypy-strict

# run every linter we have: ruff + flake8 + mypy --strict
lint-all: ruff flake8 mypy-strict

test:
	uv run pytest

test-turnin: lint-strict test

test-all: lint-all test


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# turn-in
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# The turn-in tarball is a self-contained copy of the project (source + maps +
# README), minus dev cruft, the subject PDF and the test suite (the subject
# says tests are neither submitted nor graded).
# Download it onto a school machine, extract it, and commit the tree into the
# intranet git repo.

# fail early if TAG wasn't provided
require-tag:
	@test -n "$(TAG)" || { echo "TAG is required, e.g. make dist TAG=v1.0.0"; exit 1; }

# stage the working tree (minus dev cruft) into STAGE_DIR
stage:
	rm -rf $(STAGE_DIR)
	mkdir -p $(STAGE_DIR)
	rsync -a --filter=':- .gitignore' \
		--exclude='.git/' --exclude='.jj/' --exclude='.hypothesis/' \
		--exclude='$(DIST_DIR)/' --exclude='$(TEST_DIR)/' --exclude='$(VENDOR_DIR)/'\
		--exclude='$(DOCS_DIR)'\
		./ $(STAGE_DIR)/
	cp .gitignore $(STAGE_DIR)/.gitignore

# package the staged tree into the downloadable turn-in tarball
# usage: make dist TAG=v1.0.0
dist: require-tag test-turnin stage
	tar -czf $(TURNIN) -C $(STAGE_DIR) .
	@printf '\033[1;32m✓ turn-in archive ready: %s\n\033[0m' "$(TURNIN)"

# create an annotated git tag for the current commit (if it doesn't exist yet)
# usage: make tag TAG=v1.0.0 MSG="release notes"
tag: require-tag
	@git rev-parse -q --verify "refs/tags/$(TAG)" >/dev/null \
		|| git tag $(TAG) -m "$(MSG)"

# build the turn-in tarball, tag + push, and cut a GitHub release carrying it
# usage: make publish TAG=v1.0.0 MSG="release notes"
# gh prompts interactively for the release title and notes.
publish: dist tag
	git push origin HEAD:refs/heads/main --tags
	gh release create $(TAG) $(TURNIN)

# remove python caches
clean:
	find $(SRC_DIR) $(TEST_DIR) -type d -name '__pycache__' -exec rm -rf {} +
	find $(SRC_DIR) $(TEST_DIR) -type f -name '*.pyc' -delete
	rm -rf .mypy_cache .ruff_cache .pytest_cache

# clean + remove the dist tree
fclean: clean
	rm -rf dist
