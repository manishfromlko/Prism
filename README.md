# Kubeflow Workspace Profiling Webapp

A generative AI-powered web application for profiling and analyzing Kubeflow workspaces. This project provides intelligent insights into data science workflows, ML pipelines, and collaborative patterns through advanced data ingestion, vector search, and LLM-powered analysis.

## Features

### 🚀 Current Implementation
- **Data Ingestion Pipeline**: Automated discovery and metadata extraction from Kubeflow workspaces
- **Guardrail Security**: Automatic detection and skipping of sensitive/unsupported files
- **Incremental Updates**: Efficient processing of only changed files
- **Audit Logging**: Complete compliance tracking for ingestion decisions
- **CLI Interface**: Command-line tool for easy pipeline execution

### 🔮 Upcoming Features
- **Langchain Orchestration**: Intelligent workflow analysis and chaining
- **Milvus Vector Database**: High-performance vector storage for embeddings
- **LiteLLM API Gateway**: Unified interface for multiple LLM providers
- **Langfuse Observability**: Comprehensive monitoring and tracing
- **Next.js Frontend**: Modern React-based user interface

## Prerequisites

- Python 3.11+
- pip (Python package manager)
- Git

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd project-1
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install langchain litellm pymilvus pydantic pytest
   ```

4. **Install development dependencies (optional, for code quality):**
   ```bash
   pip install black flake8
   ```

## Usage

### Running the Ingestion Pipeline

The ingestion pipeline discovers workspaces, extracts metadata from notebooks and scripts, and stores the catalog in JSON format.

#### Full Ingestion (Initial Run)
```bash
PYTHONPATH=src python -m src.ingestion.cli --root dataset --mode full
```

#### Incremental Ingestion (Update Changed Files)
```bash
PYTHONPATH=src python -m src.ingestion.cli --root dataset --mode incremental
```

#### Dry Run (Validate Without Persisting)
```bash
PYTHONPATH=src python -m src.ingestion.cli --root dataset --mode full --dry-run
```

### Command Line Options

- `--root`: Path to the workspace root directory (required)
- `--mode`: `full` or `incremental` (default: full)
- `--dry-run`: Validate without persisting changes

### Output

The pipeline creates a `.ingestion/` directory in the root path containing:
- `ingestion_catalog.json`: Workspace and artifact metadata
- `ingestion_audit.json`: Audit log of ingestion decisions

## Testing

### Run All Tests
```bash
PYTHONPATH=src python -m pytest tests/ingestion/ -v
```

### Run Specific Test Categories
```bash
# Unit tests
PYTHONPATH=src python -m pytest tests/ingestion/unit/ -v

# Integration tests
PYTHONPATH=src python -m pytest tests/ingestion/integration/ -v
```

### Test Coverage
The test suite covers:
- Data model validation
- Guardrail pattern matching
- Storage operations
- Full pipeline execution
- Incremental updates
- Audit logging

## Code Quality

### Formatting
```bash
black src/ tests/
```

### Linting
```bash
flake8 src/ tests/
```

## Project Structure

```
project-1/
├── dataset/                    # Sample workspace data for testing
├── src/
│   └── ingestion/             # Ingestion pipeline modules
│       ├── cli.py             # Command-line interface
│       ├── pipeline.py        # Core ingestion logic
│       ├── storage.py         # JSON-based persistence
│       ├── guards.py          # Security guardrails
│       ├── extractors.py      # Metadata extraction
│       ├── models.py          # Data models
│       └── utils.py           # Utility functions
├── tests/
│   └── ingestion/             # Test suite
│       ├── unit/              # Unit tests
│       └── integration/       # Integration tests
├── specs/
│   └── 001-data-ingestion-pipeline/  # Feature specifications
└── README.md                  # This file
```

## Development

### Adding New Features
1. Create a new spec in `specs/` following the naming convention
2. Implement the feature in phases with clear acceptance criteria
3. Add comprehensive tests
4. Update documentation

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file in the dataset directory for details.

## Roadmap

- [x] Data Ingestion Pipeline (MVP)
- [ ] Langchain Integration
- [ ] Vector Database Setup
- [ ] LLM Gateway Implementation
- [ ] Observability Stack
- [ ] Frontend Development
- [ ] Production Deployment</content>
<parameter name="filePath">/Users/manish/mount/projects/project-1/README.md