# NVIDIA Model Tester - Project Documentation

**Language / 语言**: [🇺🇸 English](README.md) | [🇨🇳 中文](README_ZH.md)

---

## 📖 Project Overview

**NVIDIA Model Tester** is a powerful automated testing framework specifically designed to evaluate and compare various AI models provided by the NVIDIA NIM API. It can automatically discover, classify, and test all available models, generating detailed HTML reports to help users select the most suitable models for their application scenarios.

### Core Features

- 🔍 **Automatic Model Discovery**: Automatically retrieve all available model lists from the NVIDIA API
- 🏷️ **Intelligent Classification**: Automatically classify models based on characteristics (LLM, Multimodal, Image, Audio, Specialized)
- 🧪 **Multi-dimensional Testing**: Comprehensive evaluation across four dimensions: availability, performance, capability, and quality
- 📊 **Visual Reports**: Generate beautiful interactive HTML reports with rankings, charts, and detailed analysis
- ⚡ **Concurrent Testing**: Support multi-threaded concurrent testing to significantly improve efficiency
- 💰 **Cost Estimation**: Estimate calling costs based on token usage

---

## 🏗️ Project Architecture

```
nvidia-model-tester/
├── main.py                  # Main program entry point, coordinates testing workflow
├── config.py                # Configuration management using Pydantic Settings
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variable example file
│
├── models/                  # Model management module
│   ├── scanner.py          # Model discovery and classifier
│   └── registry.py         # Model registry
│
├── tests/                   # Test suite module
│   ├── base.py             # Test base class and result data structures
│   ├── availability.py     # Availability tests
│   ├── performance.py      # Performance tests
│   ├── capability.py       # Capability tests
│   └── quality.py          # Quality evaluation tests
│
├── scenarios/              # Test scenario module
│   └── prompts.py          # Pre-defined test prompt library
│
├── reporters/              # Report generation module
│   └── html_reporter.py    # HTML report generator
│
├── utils/                  # Utility module
│   ├── api_client.py       # NVIDIA API client
│   └── metrics.py          # Metrics calculation utilities
│
└── output/                 # Output directory (auto-generated)
    └── *.html              # Generated test reports
```

---

## 🚀 Quick Start

### 1. Environment Setup

#### System Requirements
- Python 3.8 or higher
- NVIDIA API Key (obtain from [build.nvidia.com](https://build.nvidia.com))

#### Install Dependencies

```bash
# After cloning or downloading the project, enter the project directory
cd nvidia-model-tester

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

There are two ways to configure the NVIDIA API Key:

#### Method 1: Using .env file (Recommended)

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file and fill in your API Key
nano .env  # or use your preferred editor
```

Set in `.env` file:
```env
NVIDIA_API_KEY="nvapi-your-api-key-here"
```

#### Method 2: Using Environment Variables

```bash
# Windows PowerShell
$env:NVIDIA_API_KEY="nvapi-your-api-key-here"

# Linux/Mac
export NVIDIA_API_KEY="nvapi-your-api-key-here"
```

### 3. Run Tests

#### Basic Usage

```bash
# Test all discovered models
python main.py

# Test only LLM models
python main.py --scope llm

# Test 3 sample models per category (quick mode)
python main.py --scope sample

# Customize concurrency (increase speed)
python main.py --concurrency 10

# Specify output directory
python main.py --output ./my_reports

# Skip quality evaluation (save time)
python main.py --no-quality
```

#### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--scope` | Test scope: all, llm, multimodal, image, audio, specialized, sample | all |
| `--max-models` | Limit number of tested models | No limit |
| `--concurrency` | Maximum concurrent requests (1-50) | 5 |
| `--output` | Report output directory | ./output |
| `--no-quality` | Skip quality evaluation tests | Quality evaluation enabled |
| `--api-key` | Directly pass API Key | Read from environment variable |

---

## 🧪 Test Dimensions Explained

The project provides four-dimensional testing, with each dimension focusing on different model characteristics:

### 1. Availability Test

**Purpose**: Verify that model endpoints are accessible and responding normally

**Test Content**:
- API health check
- Minimal chat completion test (send simple request)
- Consistency verification (multiple requests to ensure stability)

**Scoring Criteria**:
- Success rate ≥ 50% considered passing
- Score = Successful attempts / Total attempts

**Applicable Models**: All chat models (LLM, Multimodal)

### 2. Performance Test

**Purpose**: Measure model response speed and throughput

**Test Content**:
- **TTFT** (Time To First Token): First token latency, measures user-perceived response speed
- **Total Latency**: Time required for complete response
- **Throughput**: Tokens generated per second

**Scoring Algorithm** (Weighted Composite):
```
Total Score = TTFT Score × 40% + Latency Score × 30% + Throughput Score × 30%

TTFT Score:
  < 500ms   → 1.0
  > 10000ms → 0.0
  Linear interpolation

Latency Score:
  < 5000ms  → 1.0
  > 30000ms → 0.0
  Linear interpolation

Throughput Score:
  > 100 tok/s → 1.0
  < 5 tok/s   → 0.0
  Linear interpolation
```

**Repeated Testing**: Execute 3 times by default and take average for stable results

### 3. Capability Test

**Purpose**: Evaluate model performance in various real-world scenarios

**Test Scenario Library** (12 scenarios):

| Scenario ID | Name | Description | Weight |
|-------------|------|-------------|--------|
| general_chat | General Chat | Basic instruction following and common sense Q&A | 3 |
| code_generation | Code Generation | Write complex functions | 5 |
| code_debugging | Code Debugging | Identify and fix code errors | 4 |
| math_reasoning | Math Reasoning | Multi-step mathematical problem solving | 4 |
| logical_reasoning | Logical Reasoning | Complex reasoning under constraints | 5 |
| creative_writing | Creative Writing | Generate creative text | 2 |
| summarization | Text Summarization | Condense long text while preserving key information | 3 |
| translation | Translation | English to Chinese accuracy test | 2 |
| agentic_reasoning | Agentic Planning | Multi-step tool usage planning | 4 |
| long_context | Long Context Understanding | Extract information from long documents | 3 |
| multimodal_understanding | Multimodal Understanding | Spatial understanding and detailed description | 2 |
| instruction_following | Constrained Instruction Following | Precisely follow format and content constraints | 4 |

**Scoring Method**:
- Use LLM-as-Judge method with strong reference model to evaluate answer quality
- Compare against expected traits (e.g., "accurate", "clear", "step-by-step reasoning")
- Aggregate scores from all scenarios to get overall capability score

### 4. Quality Evaluation

**Purpose**: Deeply evaluate model output quality and reliability

**Test Method**:
- Use high-quality reference model (default: `nvidia/llama-3.3-nemotron-super-49b-v1`) as judge
- Fine-grained scoring of model responses
- Evaluate relevance, accuracy, and completeness of answers

**Note**: This test is time-consuming and can be skipped with `--no-quality` parameter

---

## 📊 Report Interpretation

After testing completes, an HTML report will be generated in the `output/` directory with filename format: `nvidia_report_YYYYMMDD_HHMMSS.html`

### Report Structure

#### 1. Executive Summary

Displays key statistics:
- Total number of tested models
- Number of categories covered
- Number of models passing all tests
- Average score
- Best model

#### 2. Overall Rankings

- **Bar Chart**: Intuitively displays composite scores of top 20 models
- **Ranking Table**:
  - Rank
  - Model ID and category
  - Composite score (with progress bar)
  - Test result tags for each dimension (green=pass, red=fail)

#### 3. Per-Dimension Analysis

Separately displays Top 5 models for each dimension:
- Availability Top 5
- Performance Top 5
- Capability Top 5
- Quality Top 5

Helps identify models that excel in specific areas.

#### 4. Scenario Suitability Matrix

Heatmap showing model performance across different scenarios:
- Rows: Models (Top 20)
- Columns: Test scenarios
- Color coding:
  - 🟢 Dark Green: 0.8-1.0 (Excellent)
  - 🟡 Yellow: 0.6-0.8 (Good)
  - 🟠 Orange: 0.4-0.6 (Fair)
  - 🔴 Red: < 0.4 (Poor)

**Use Case**: Quickly find models suitable for specific application scenarios

#### 5. Cost & Token Consumption

Estimate calling costs for each model:
- Total tokens
- Prompt tokens (input)
- Completion tokens (output)
- Estimated cost (USD)

**Cost Calculation Formula**:
```
Cost = (Input Tokens/1000 × $0.0001) + (Output Tokens/1000 × $0.0004)
```

*Note: Rates can be customized in configuration*

#### 6. Detailed Model Cards

Detailed information for each model, collapsible:
- Basic model information (ID, category, overall score)
- Test results and detailed metrics for each dimension
- Error messages (if any)

**Click model name to expand/collapse details**

---

## ⚙️ Configuration Details

Configuration file located at `config.py`, uses Pydantic Settings for management, supports environment variable overrides.

### Main Configuration Items

```python
# API Configuration
NVIDIA_API_KEY: str           # API Key (required)
NVIDIA_API_BASE: str          # API base URL (default: https://integrate.api.nvidia.com/v1)

# Test Scope
TEST_SCOPE: TestScope         # Test scope enum (all/llm/multimodal/image/audio/specialized/sample)
MAX_MODELS: Optional[int]     # Maximum number of tested models (None=all)
CONCURRENCY: int              # Concurrency (1-50, default 5)
REQUEST_TIMEOUT: int          # Request timeout in seconds (default 120)

# Test Parameters
TEST_REPEAT: int              # Repeat count per test (1-10, default 3)
MAX_TOKENS_GENERATE: int      # Max tokens for generation tasks (default 512)
MAX_TOKENS_LONG_CONTEXT: int  # Max tokens for long context tests (default 4096)

# Output Configuration
OUTPUT_DIR: str               # Output directory (default ./output)
REPORT_FORMAT: ReportFormat   # Report format (html/json/both, default both)
REPORT_TITLE: str             # Report title

# Cost Estimation
COST_PER_1K_INPUT_TOKENS: float   # Cost per 1k input tokens (default $0.0001)
COST_PER_1K_OUTPUT_TOKENS: float  # Cost per 1k output tokens (default $0.0004)

# Quality Evaluation
QUALITY_REFERENCE_MODEL: str      # Reference model (default llama-3.3-nemotron-super-49b-v1)
ENABLE_QUALITY_EVAL: bool         # Enable quality evaluation (default True)
```

### Override Configuration with Environment Variables

All configuration items can be overridden via environment variables with prefix `NV_TEST_`:

```bash
# Examples
export NV_TEST_CONCURRENCY=10
export NV_TEST_TEST_SCOPE=llm
export NV_TEST_OUTPUT_DIR=./my_output
export NV_TEST_ENABLE_QUALITY_EVAL=false
```

---

## 🔧 Advanced Usage

### Custom Test Scenarios

Edit `scenarios/prompts.py` to add new test scenarios:

```python
MY_CUSTOM_SCENARIO = TestPrompt(
    id="my_scenario",
    label="My Custom Scenario",
    description="Scenario description",
    messages=[
        {"role": "user", "content": "Your test prompt"}
    ],
    tags=["llm"],  # Applicable model categories
    weight=4,      # Weight 1-5
    expected_traits=["accurate", "detailed"],  # Expected response traits
)

# Add to ALL_PROMPTS list
ALL_PROMPTS.append(MY_CUSTOM_SCENARIO)
```

### Extend Test Dimensions

Create new test classes by inheriting from `BaseTester`:

```python
from tests.base import BaseTester, TestResult
from models.scanner import ModelInfo

class MyCustomTester(BaseTester):
    def name(self) -> str:
        return "my_test"
    
    def description(self) -> str:
        return "My custom test description"
    
    def test_model(self, model: ModelInfo) -> TestResult:
        # Implement test logic
        # ...
        
        return TestResult(
            model_id=model.id,
            test_name=self.name(),
            passed=True,
            score=0.95,
            details={"metric1": value1, "metric2": value2},
            errors=[]
        )
```

Then register in `main.py`:

```python
testers.append(MyCustomTester(client))
```

### Batch Test Different Configurations

```bash
# Test performance impact of different concurrency levels
for concurrency in 1 5 10 20; do
    python main.py --scope sample --concurrency $concurrency --output "./results/conc_$concurrency"
done
```

---

## 📈 Performance Optimization Tips

### 1. Adjust Concurrency

- **Low concurrency (1-3)**: Suitable for testing few critical models, avoid API rate limiting
- **Medium concurrency (5-10)**: Balance speed and stability, recommended default
- **High concurrency (10-50)**: Fast testing of many models, but may trigger rate limits

### 2. Use Sampling Mode

```bash
# Quickly understand representative models per category
python main.py --scope sample --concurrency 10
```

### 3. Skip Time-Consuming Tests

```bash
# Skip quality evaluation (most time-consuming test)
python main.py --no-quality
```

### 4. Limit Model Count

```bash
# Test only first 20 models
python main.py --max-models 20
```

### 5. Test Specific Categories

```bash
# Test only LLM models
python main.py --scope llm

# Test only multimodal models
python main.py --scope multimodal
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. API Key Not Set

**Error Message**:
```
WARNING: NVIDIA_API_KEY is not set.
❌ Failed to discover models: 401 Unauthorized
```

**Solution**:
```bash
# Check environment variable
echo $NVIDIA_API_KEY  # Linux/Mac
echo $env:NVIDIA_API_KEY  # Windows

# Or configure correctly in .env file
```

#### 2. Request Timeout

**Error Message**:
```
httpx.ReadTimeout: timed out
```

**Solution**:
```bash
# Increase timeout
export NV_TEST_REQUEST_TIMEOUT=180

# Or reduce concurrency to decrease server load
python main.py --concurrency 3
```

#### 3. Rate Limiting

**Error Message**:
```
429 Too Many Requests
```

**Solution**:
```bash
# Reduce concurrency
python main.py --concurrency 2

# Test in batches
python main.py --scope llm --max-models 10
```

#### 4. Model Unavailable

Some models may be temporarily unavailable during testing, which is normal. The report will mark these models as failed in availability tests.

#### 5. Insufficient Memory

Testing many models may consume significant memory:

**Solution**:
```bash
# Reduce concurrency
python main.py --concurrency 3

# Or test in batches
python main.py --scope llm
python main.py --scope multimodal
```

---

## 📝 Output Examples

### Console Output

```
============================================================
  NVIDIA Model Tester
  Started: 2026-05-18 12:10:52
============================================================

🔍 Phase 1: Discovering models from NVIDIA API...
  Found 150 models
  After filter (all): 150 models
    audio: 12
    image: 18
    llm: 85
    multimodal: 20
    specialized: 15

🧪 Phase 2: Running tests (concurrency=5)...

  📌 Test suite: availability (Check API reachability...)
    ✅ nvidia/llama-3.3-nemotron-super-49b-v1          score=1.000
    ✅ nvidia/mistral-large                              score=0.950
    ❌ some-broken-model                                 score=0.333

  📌 Test suite: performance (Measure TTFT, latency...)
    ✅ nvidia/llama-3.3-nemotron-super-49b-v1          score=0.850
    ...

📝 Phase 3: Generating report...
  📄 Report saved to: ./output/nvidia_report_20260518_121052.html

============================================================
  SUMMARY
============================================================
  Rank  Model                                              Score   
  ---------------------------------------------------------------
  1     nvidia/llama-3.3-nemotron-super-49b-v1           0.923
  2     nvidia/mistral-large                               0.887
  3     meta/llama-3.1-405b-instruct                       0.856
  ...

✅ Done. Report: ./output/nvidia_report_20260518_121052.html
```

### HTML Report

Open the generated HTML file to see:
- Modern dark-themed interface
- Interactive bar charts and heatmaps
- Collapsible model detail cards
- Responsive design supporting mobile viewing

---

## 🤝 Contributing Guidelines

Welcome to contribute code, report issues, or suggest improvements!

### Development Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd nvidia-model-tester

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install pytest black flake8
```

### Code Standards

- Follow PEP 8 style guide
- Use type annotations
- Write clear docstrings
- Keep functions with single responsibility

### Submit Pull Request

1. Fork this repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🔗 Related Links

- [NVIDIA NIM API Documentation](https://docs.nvidia.com/nim/)
- [NVIDIA Build Portal](https://build.nvidia.com)
- [OpenAI API Compatible Interface](https://platform.openai.com/docs/api-reference)

---

## 📞 Support & Feedback

For questions or suggestions:
1. Check the troubleshooting section of this document
2. View GitHub Issues
3. Submit a new Issue describing your problem

---

**Happy Testing!** 🚀

---

[🇨🇳 中文版文档](README_ZH.md)
