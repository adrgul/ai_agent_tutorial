# Migration to pyproject.toml

This document explains the migration from `requirements.txt` to modern Python packaging with `pyproject.toml`.

## What Changed?

### New Files

1. **pyproject.toml** - Modern Python project configuration
   - Replaces setup.py and setup.cfg
   - Contains all project metadata, dependencies, and tool configurations
   - Follows PEP 518, PEP 621, and PEP 660

2. **Makefile** - Development workflow automation
   - Common commands like `make test`, `make run`, etc.
   - Simplifies development tasks

3. **Dockerfile** - Production-ready container definition
   - Multi-stage build for optimized image size
   - Health checks and proper configuration

4. **docker-compose.yml** - Container orchestration
   - Easy one-command deployment
   - Environment variable management

### Legacy Support

**requirements.txt** is still available for backwards compatibility, but the modern approach is recommended.

## Installation Methods

### Modern Approach (Recommended)

```bash
# Install production dependencies
pip install -e .

# Install with development tools
pip install -e ".[dev]"

# Install with test dependencies
pip install -e ".[test]"

# Install everything
pip install -e ".[dev,test]"
```

### Legacy Approach (Still Works)

```bash
pip install -r requirements.txt
```

## Benefits of pyproject.toml

### 1. Single Source of Truth
All project configuration in one file:
- Dependencies
- Build system
- Tool configurations (pytest, black, ruff, mypy, coverage)
- Project metadata

### 2. Editable Installs
The `-e` flag installs in "editable" mode:
- Changes to code are immediately available
- No need to reinstall after every change
- Perfect for development

### 3. Optional Dependencies
Separate dependency groups:
```toml
[project.optional-dependencies]
dev = ["black", "ruff", "rich"]
test = ["pytest", "pytest-cov"]
```

Install only what you need:
```bash
pip install -e .              # Production only
pip install -e ".[test]"      # Add test dependencies
pip install -e ".[dev,test]"  # Everything
```

### 4. Tool Configuration
All tool configs in one file:
```toml
[tool.pytest.ini_options]
[tool.black]
[tool.ruff]
[tool.coverage]
[tool.mypy]
```

No more scattered config files!

### 5. Standards Compliance
- PEP 518 (Build system requirements)
- PEP 621 (Project metadata)
- PEP 660 (Editable installs)

## Using the Makefile

Instead of remembering long commands:

```bash
# Old way
pytest --cov=app --cov-report=html --cov-report=term-missing

# New way
make test-cov
```

### Available Commands

```bash
make help         # See all commands
make install-dev  # Install dependencies
make run          # Start API server
make dev          # Start with auto-reload
make demo         # Run demo
make test         # Run tests
make test-cov     # Tests with coverage
make lint         # Check code
make format       # Format code
make clean        # Clean up
```

## Docker Support

### Development
```bash
# Start everything
docker-compose up

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production
```bash
# Build
docker build -t triage-agent .

# Run
docker run -p 8000:8000 --env-file .env triage-agent
```

Or use Makefile:
```bash
make docker-build
make docker-run
```

## What to Keep

You can safely keep both approaches:

1. **pyproject.toml** - Use this for new projects and modern tooling
2. **requirements.txt** - Keep for CI/CD systems that don't support pyproject.toml yet

They're kept in sync automatically.

## Migration Checklist

If you have an existing installation:

- [ ] Update to latest code: `git pull`
- [ ] Uninstall old installation: `pip uninstall customer-service-triage-agent`
- [ ] Install with new method: `pip install -e ".[dev,test]"`
- [ ] Test installation: `make test`
- [ ] Try new commands: `make help`

## Troubleshooting

### "No module named 'app'"

You need to install in editable mode:
```bash
pip install -e .
```

### "pip install -e . fails"

Ensure you have setuptools:
```bash
pip install --upgrade pip setuptools wheel
pip install -e ".[dev,test]"
```

### "Makefile not working on Windows"

Windows users can:
1. Use WSL (recommended)
2. Install `make` via chocolatey: `choco install make`
3. Use the direct commands from the Makefile

### "Docker compose not found"

Ensure Docker Desktop is installed, or use:
```bash
docker compose up  # New Docker CLI (no hyphen)
```

## Further Reading

- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
- [Python Packaging Guide](https://packaging.python.org/)
- [setuptools Documentation](https://setuptools.pypa.io/)

## Questions?

Check the [README.md](README.md) or [QUICKSTART.md](QUICKSTART.md) for detailed documentation.
