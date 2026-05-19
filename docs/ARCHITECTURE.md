# Technical Architecture Document

**Language / 语言**: [🇺🇸 English](ARCHITECTURE.md) | [🇨🇳 中文](ARCHITECTURE_ZH.md)

---

## 🏛️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     NVIDIA Model Tester                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌────────────────┐   ┌────────────────┐
│  Configuration │   │  API Client    │   │  Model Scanner │
│  (config.py)   │   │ (api_client)   │   │  (scanner.py)  │
└───────────────┘   └────────────────┘   └────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Test Runner   │
                    │   (main.py)     │
                    └─────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐   ┌────────────────┐   ┌────────────────┐
│ Availability │   │  Performance   │   │  Capability    │
│   Tester     │   │    Tester      │   │    Tester      │
└──────────────┘   └────────────────┘   └────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  HTML Reporter  │
                    │ (html_reporter) │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    Web UI       │
                    │  (web_ui.py)    │
                    │  HTTP Server    │
                    └─────────────────┘
```

---

## 📦 Module Structure

### 1. Configuration Module (`config.py`)

**Responsibility**: Centralized configuration management

**Key Components**:
- `Settings` class: Pydantic-based configuration with validation
- Environment variable support via `.env` file
- Type-safe configuration with default values

**Configuration Categories**:
- API settings (key, base URL, timeout)
- Test parameters (scope, concurrency, retries)
- Output settings (directory, format)
- Cost estimation rates
- Quality evaluation options

### 2. API Client Module (`utils/api_client.py`)

**Responsibility**: Communicate with NVIDIA NIM API

**Key Features**:
- **Rate Limiter**: Sliding window algorithm to avoid 429 errors (40 req/min limit)
- **Retry Mechanism**: Exponential backoff for failed requests
- **Thread Safety**: Shared rate limiter across all client instances
- **OpenAI-Compatible**: Standard chat/completion endpoints

**Main Methods**:
- `health_check()`: Verify API availability
- `list_models()`: Fetch available models
- `chat_completion()`: Non-streaming chat requests
- `timed_chat()`: Streaming chat with performance metrics (TTFT, throughput)
- `completion()`: Legacy completion endpoint

### 3. Model Scanner Module (`models/scanner.py`)

**Responsibility**: Discover and classify models

**Workflow**:
1. Fetch model list from API
2. Extract metadata (ID, name, publisher)
3. Classify by category using keyword matching
4. Generate human-readable names

**Classification Rules**:
- **LLM**: llama, nemotron, mistral, qwen, gemma, etc.
- **Multimodal**: vlm, vision, nvlm, kimi, etc.
- **Image**: stable-diffusion, flux, sdxl, etc.
- **Audio**: asr, tts, riva, voicechat, etc.
- **Specialized**: safety, rerank, ocr, guard, etc.

**Helper Functions**:
- `discover_models()`: Main discovery function
- `group_by_category()`: Group models by type
- `sample_models()`: Select representative samples

### 4. Test Framework (`tests/`)

#### Base Classes (`tests/base.py`)

**`TestResult` Dataclass**:
```python
model_id: str          # Tested model ID
test_name: str         # Test suite name
passed: bool           # Pass/fail status
score: float           # Score 0.0-1.0
details: dict          # Detailed metrics
errors: list[str]      # Error messages
warnings: list[str]    # Warning messages
```

**`BaseTester` Abstract Class**:
- `name()`: Return test suite identifier
- `description()`: Human-readable description
- `test_model(model)`: Execute tests and return results
- `skip_reason(model)`: Optional skip logic

#### Availability Tester (`tests/availability.py`)

**Purpose**: Verify model endpoint accessibility

**Test Process**:
1. Send minimal chat request
2. Repeat 3 times for consistency
3. Calculate success rate

**Scoring**: Success count / Total attempts

#### Performance Tester (`tests/performance.py`)

**Purpose**: Measure response speed and throughput

**Metrics Collected**:
- TTFT (Time To First Token): User-perceived latency
- Total latency: Complete response time
- Tokens per second: Generation throughput

**Scoring Algorithm**:
```python
TTFT Score (40% weight):
  < 500ms → 1.0, > 10000ms → 0.0, linear interpolation

Latency Score (30% weight):
  < 5000ms → 1.0, > 30000ms → 0.0, linear interpolation

Throughput Score (30% weight):
  > 100 tok/s → 1.0, < 5 tok/s → 0.0, linear interpolation
```

**Execution**: Default 3 repeats, average results

#### Capability Tester (`tests/capability.py`)

**Purpose**: Evaluate model performance across scenarios

**Scenario Library** (12 scenarios in `scenarios/prompts.py`):
- General chat, code generation/debugging
- Math/logical reasoning
- Creative writing, summarization, translation
- Agentic planning, long context, multimodal
- Instruction following

**Testing Method**:
1. Send scenario-specific prompts
2. Collect model responses
3. Calculate token usage
4. Score based on expected traits

**Scoring**: Aggregate weighted scenario scores

#### Quality Tester (`tests/quality.py`)

**Purpose**: Deep quality evaluation using LLM-as-Judge

**Method**:
1. Use strong reference model as judge
2. Compare test model output against reference
3. Score on relevance, accuracy, completeness

**Note**: Most time-consuming test, can be skipped with `--no-quality`

### 5. Scenario Prompts (`scenarios/prompts.py`)

**`TestPrompt` Dataclass**:
```python
id: str                    # Unique identifier
label: str                 # Human-readable name
description: str           # What this evaluates
messages: list[dict]       # Chat messages (OpenAI format)
tags: list[str]            # Applicable model categories
weight: int                # Importance 1-5
expected_traits: list[str] # Expected response qualities
reference_answer: str      # Optional reference answer
```

**Scenario Design Principles**:
- Cover diverse real-world use cases
- Varying difficulty levels
- Different skill domains
- Balanced weights for fair scoring

### 6. Metrics Utilities (`utils/metrics.py`)

**Data Classes**:
- `TimingMetrics`: Aggregate TTFT, latency, throughput
- `AvailabilityMetrics`: Track success/failure rates
- `QualityMetrics`: Scenario-based quality scores
- `CostMetrics`: Token usage and cost tracking

**Helper Functions**:
- `_safe_mean()`, `_safe_min()`: Safe statistical calculations
- `_safe_percentile()`: Percentile calculation (e.g., P95)
- Handle empty lists gracefully

### 7. HTML Reporter (`reporters/html_reporter.py`)

**Purpose**: Generate comprehensive visual reports

**Report Sections**:
1. **Executive Summary**: Key statistics cards
2. **Overall Rankings**: Bar chart + ranking table (Top 30)
3. **Per-Dimension Analysis**: Top 5 per dimension
4. **Scenario Suitability Matrix**: Heatmap (Top 20 models × scenarios)
5. **Cost Analysis**: Token usage and estimated costs
6. **Detailed Model Cards**: Expandable details for each model

**Technical Implementation**:
- Self-contained HTML (embedded CSS + JavaScript)
- Canvas-based bar charts (zero dependencies)
- Color-coded score indicators (green/orange/red)
- Responsive design for mobile viewing
- **Bilingual Support**: Toggle between Chinese/English

**Language Toggle Feature**:
```javascript
// Click button to switch language
function toggleLanguage() {
  currentLang = currentLang === 'zh' ? 'en' : 'zh';
  // Update all elements with data-zh/data-en attributes
}
```

---

### 8. Web UI Console (`web_ui.py`)

**Tech Stack**: Python built-in `http.server` module (zero external dependencies)

**Responsibility**:
- Provide a browser-based test control interface
- RESTful API backend (model listing, test execution, status polling, report serving)
- Background test execution thread reusing existing test framework

**API Endpoints**:

| Endpoint | Method | Function |
|----------|--------|----------|
| `/` | GET | Web console page |
| `/api/models` | GET | Fetch all models from NVIDIA API |
| `/api/run` | POST | Start background test thread |
| `/api/status` | GET | Real-time test progress query |
| `/api/report?path=...` | GET | View generated HTML report |

**Design Features**:
- ✅ Single-file deployment, zero external dependencies
- ✅ Self-contained HTML (inline CSS + JavaScript)
- ✅ Real-time concurrency validation (NVIDIA 40 req/min limit)
- ✅ Model search filtering + category quick-select
- ✅ API call count and time estimation

---

## 🔄 Data Flow

### Phase 1: Discovery
```
NVIDIA API → NIMClient.list_models() → ModelInfo objects
                                      ↓
                              Keyword classification
                                      ↓
                          Categorized model list
```

### Phase 2: Testing
```
Model List → ThreadPoolExecutor (concurrent)
                  ↓
          ┌───────┴───────┐
          ↓               ↓
   Availability Test   Skip if fails
          ↓
   Performance Test
          ↓
   Capability Test
          ↓
   Quality Test (optional)
          ↓
   TestResult objects
```

### Phase 3: Reporting
```
TestResults → ModelReportData aggregation
                   ↓
           Calculate overall scores
                   ↓
           Generate HTML report
                   ↓
           Save to output directory
```

---

## 🎯 Design Patterns

### 1. Strategy Pattern
Different test types implement common `BaseTester` interface, allowing easy extension.

### 2. Factory Pattern
`discover_models()` creates appropriate `ModelInfo` objects based on API response.

### 3. Observer Pattern
Real-time console output during testing provides progress feedback.

### 4. Singleton Pattern
Global `settings` object ensures consistent configuration access.

### 5. Template Method Pattern
`BaseTester` defines test execution skeleton, subclasses implement specifics.

---

## 🔐 Thread Safety

### Rate Limiter
```python
class RateLimiter:
    requests: deque      # Thread-safe with Lock
    lock: Lock           # Protects shared state
    
    def record_request():
        with self.lock:  # Acquire lock
            self.requests.append(time.time())
```

### Concurrent Testing
- `ThreadPoolExecutor` manages worker threads
- Each thread gets independent `NIMClient` instance
- Shared `_rate_limiter` coordinates across threads
- No shared mutable state in testers

---

## 📊 Scoring System

### Overall Score Calculation
```python
overall_score = mean(all_test_scores)
```

### Dimension Scores
Each test returns 0.0-1.0 score based on:
- **Availability**: Success rate
- **Performance**: Weighted composite of TTFT/latency/throughput
- **Capability**: Weighted average of scenario scores
- **Quality**: LLM-as-judge evaluation

### Color Coding
- 🟢 Green: ≥ 0.7 (Good)
- 🟡 Orange: 0.4 - 0.7 (Fair)
- 🔴 Red: < 0.4 (Poor)

---

## 🚀 Performance Considerations

### Concurrency Control
- Default: 5 concurrent requests
- Configurable: 1-50 via `--concurrency`
- Rate limiter prevents API throttling

### Memory Management
- Stream processing for large responses
- Incremental result collection
- No unnecessary data retention

### Optimization Tips
1. Use `--scope sample` for quick overview
2. Skip quality eval with `--no-quality`
3. Adjust concurrency based on API limits
4. Batch test different scopes separately

---

## 🧪 Extensibility

### Adding New Test Dimensions
```python
class MyNewTester(BaseTester):
    def name(self) -> str:
        return "my_test"
    
    def test_model(self, model: ModelInfo) -> TestResult:
        # Implement test logic
        return TestResult(...)

# Register in main.py
testers.append(MyNewTester(client))
```

### Adding New Scenarios
```python
NEW_SCENARIO = TestPrompt(
    id="new_scenario",
    label="New Scenario",
    description="Description",
    messages=[...],
    tags=["llm"],
    weight=4
)
ALL_PROMPTS.append(NEW_SCENARIO)
```

### Custom Report Formats
Extend `HTMLReporter` or create new reporter class implementing similar interface.

---

## 📝 Code Organization Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Separation of Concerns**: API, testing, reporting are separate
3. **Dependency Injection**: Clients passed to testers, not created internally
4. **Type Safety**: Extensive use of type hints and Pydantic validation
5. **Documentation**: Comprehensive docstrings for all public APIs

---

## 🔗 Integration Points

### External Dependencies
- **httpx**: Async HTTP client for API calls
- **pydantic**: Configuration validation
- **pydantic-settings**: Environment variable integration

### API Compatibility
- OpenAI-compatible endpoints
- Standard chat/completion formats
- Streaming support for performance metrics

### Output Formats
- HTML: Interactive visual reports
- JSON: Machine-readable data export
- Console: Real-time progress updates

---

## 🎓 Learning Path

### For Beginners
1. Start with `main.py` to understand workflow
2. Read `config.py` for configuration options
3. Try running tests with different scopes

### For Developers
1. Study `tests/base.py` for test framework
2. Explore `utils/api_client.py` for API interaction
3. Review `reporters/html_reporter.py` for report generation

### For Contributors
1. Understand architecture from this document
2. Check `CONTRIBUTING.md` for guidelines
3. Start with small enhancements or bug fixes

---

**End of Architecture Document**

[🇨🇳 中文版](ARCHITECTURE_ZH.md) | [🇺🇸 English](ARCHITECTURE.md)
