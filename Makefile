# =============================================================================
# HireMatch — Developer Makefile
# =============================================================================
# Usage:
#   make test          → run the full test suite
#   make test-unit     → unit tests only
#   make test-int      → integration tests only
#   make cov           → full suite + HTML coverage report
#   make cov-term      → full suite + terminal coverage report
#   make lint          → flake8 + isort check + black check
#   make fmt           → auto-format with black + isort
#   make clean         → remove build artefacts
# =============================================================================

PYTHON  := python3
PYTEST  := $(PYTHON) -m pytest
PIP     := $(PYTHON) -m pip

# Source roots for coverage tracking
SRC     := core app utils

# ---------------------------------------------------------------------------
# Test targets
# ---------------------------------------------------------------------------

.PHONY: test
test:
	$(PYTEST) tests/

.PHONY: test-unit
test-unit:
	$(PYTEST) tests/ -m "not integration" --ignore=tests/test_integration_pipeline.py

.PHONY: test-int
test-int:
	$(PYTEST) tests/test_integration_pipeline.py -v

.PHONY: test-parser
test-parser:
	$(PYTEST) tests/test_parser.py -v

.PHONY: test-scorer
test-scorer:
	$(PYTEST) tests/test_scorer.py tests/test_scorer_extended.py -v

.PHONY: test-preprocessor
test-preprocessor:
	$(PYTEST) tests/test_preprocessor.py -v

.PHONY: test-skills
test-skills:
	$(PYTEST) tests/test_skill_extractor.py -v

.PHONY: test-routes
test-routes:
	$(PYTEST) tests/test_routes.py -v

# Run tests and stop on first failure
.PHONY: test-fast
test-fast:
	$(PYTEST) tests/ -x -q

# ---------------------------------------------------------------------------
# Coverage targets
# ---------------------------------------------------------------------------

.PHONY: cov
cov:
	$(PYTEST) tests/ --cov=$(SRC) --cov-report=html --cov-report=term-missing
	@echo ">>> HTML report: htmlcov/index.html"

.PHONY: cov-term
cov-term:
	$(PYTEST) tests/ --cov=$(SRC) --cov-report=term-missing

.PHONY: cov-xml
cov-xml:
	$(PYTEST) tests/ --cov=$(SRC) --cov-report=xml

# ---------------------------------------------------------------------------
# Linting & formatting
# ---------------------------------------------------------------------------

.PHONY: lint
lint:
	$(PYTHON) -m flake8 $(SRC) tests/ --max-line-length=88 --extend-ignore=E203,W503
	$(PYTHON) -m isort $(SRC) tests/ --check-only --diff
	$(PYTHON) -m black $(SRC) tests/ --check

.PHONY: fmt
fmt:
	$(PYTHON) -m isort $(SRC) tests/
	$(PYTHON) -m black $(SRC) tests/

# ---------------------------------------------------------------------------
# Dev environment
# ---------------------------------------------------------------------------

.PHONY: install
install:
	$(PIP) install -r requirements-dev.txt

.PHONY: install-prod
install-prod:
	$(PIP) install -r requirements.txt

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean:
	find . -type d -name __pycache__ -not -path "./.git/*" | xargs rm -rf
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache htmlcov .coverage coverage.xml

.PHONY: clean-uploads
clean-uploads:
	rm -rf uploads/* outputs/*

# ---------------------------------------------------------------------------
# Run server (dev)
# ---------------------------------------------------------------------------

.PHONY: run
run:
	$(PYTHON) run.py

.PHONY: help
help:
	@echo ""
	@echo "  HireMatch Makefile targets"
	@echo "  --------------------------"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Unit tests only (no integration)"
	@echo "  make test-int        Integration tests only"
	@echo "  make test-parser     Parser tests only"
	@echo "  make test-scorer     Scorer + extended scorer tests"
	@echo "  make test-skills     Skill extractor tests"
	@echo "  make test-routes     Flask route tests"
	@echo "  make test-fast       Stop at first failure (fast feedback)"
	@echo "  make cov             Full suite + HTML coverage report"
	@echo "  make cov-term        Full suite + terminal coverage"
	@echo "  make lint            Flake8 + isort + black checks"
	@echo "  make fmt             Auto-format (black + isort)"
	@echo "  make install         Install dev dependencies"
	@echo "  make clean           Remove cache & build artefacts"
	@echo "  make run             Start Flask dev server"
	@echo ""
