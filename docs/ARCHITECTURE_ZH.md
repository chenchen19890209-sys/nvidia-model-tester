# 技术架构文档

**Language / 语言**: [🇨🇳 中文](ARCHITECTURE_ZH.md) | [🇺🇸 English](ARCHITECTURE.md)

---

## 🏛️ 系统架构概览

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
                    │  Report Output  │
                    │   (*.html)      │
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

## 📦 核心模块详解

### 1. 配置管理模块 (config.py)

**技术栈**：Pydantic Settings

**职责**：
- 集中管理所有配置参数
- 支持环境变量覆盖
- 提供类型安全和验证

**关键设计**：

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",              # 从 .env 文件读取
        env_prefix="NV_TEST_",        # 环境变量前缀
    )
    
    # 配置项使用 Field 定义默认值和验证规则
    CONCURRENCY: int = Field(
        default=5,
        ge=1, le=50,                  # 验证范围
    )
```

**优势**：
- ✅ 自动类型转换和验证
- ✅ 优先级：命令行 > 环境变量 > .env 文件 > 默认值
- ✅ IDE 智能提示支持

---

### 2. API 客户端模块 (utils/api_client.py)

**技术栈**：httpx (异步 HTTP 客户端)

**职责**：
- 封装 NVIDIA NIM API 调用
- 处理认证、超时、错误
- 提供流式和非流式接口

**核心方法**：

| 方法 | 功能 | 返回 |
|------|------|------|
| `health_check()` | API 健康检查 | (bool, float) |
| `list_models()` | 获取模型列表 | List[Dict] |
| `chat_completion()` | 聊天完成（非流式） | Dict |
| `timed_chat()` | 聊天完成（流式+计时） | Dict with timing |
| `completion()` | 文本补全（非聊天） | Dict |

**设计亮点**：

```python
def timed_chat(self, model, messages, ...):
    """流式请求，精确测量 TTFT 和总延迟"""
    start = time.perf_counter()
    first_chunk_time = None
    
    with client.stream("POST", url, ...) as resp:
        for line in resp.iter_lines():
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()  # 记录首字时间
            # 处理内容...
    
    return {
        "timing_ms": {
            "ttft": first_chunk_time - start,      # 首字延迟
            "total": total_elapsed,                 # 总延迟
            "after_first": total - ttft,           # 后续生成时间
        }
    }
```

---

### 3. 模型扫描器 (models/scanner.py)

**职责**：
- 从 API 获取原始模型列表
- 基于关键词规则自动分类
- 提取和规范化元数据

**分类算法**：

```python
_CATEGORY_RULES = [
    # (类别, 关键词, 标签集合)
    ("image", "stable-diffusion", {"text-to-image"}),
    ("llm", "llama", {"text-generation"}),
    ("multimodal", "vlm", {"vision"}),
    # ... 更多规则
]

def _classify(model_id, name):
    """基于 ID 和名称的关键词匹配进行分类"""
    combined = f"{model_id} {name}".lower()
    
    for category, keyword, tags in _CATEGORY_RULES:
        if keyword in combined:
            return category, list(tags)
    
    return "llm", ["text-generation"]  # 默认类别
```

**分类类别**：
- `llm`：语言模型（Llama、Mistral、Qwen 等）
- `multimodal`：多模态模型（VLM、Kimi 等）
- `image`：图像生成模型（Stable Diffusion、Flux 等）
- `audio`：音频模型（ASR、TTS、Voice 等）
- `specialized`：专用模型（安全、重排序、OCR 等）

---

### 4. 测试框架 (tests/)

#### 基类设计 (base.py)

```python
class BaseTester(ABC):
    """抽象测试器，定义测试接口"""
    
    @abstractmethod
    def name(self) -> str:
        """测试套件标识符"""
    
    @abstractmethod
    def description(self) -> str:
        """人类可读的描述"""
    
    @abstractmethod
    def test_model(self, model: ModelInfo) -> TestResult:
        """执行测试并返回结果"""
    
    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        """判断是否跳过该模型"""
```

**设计模式**：策略模式（Strategy Pattern）
- 每个测试维度是一个独立的策略
- 易于扩展新测试类型
- 统一的接口和结果格式

#### 测试结果数据结构

```python
@dataclass
class TestResult:
    model_id: str
    test_name: str
    passed: bool              # 是否通过
    score: float              # 0.0 - 1.0
    details: Dict[str, Any]   # 详细指标
    errors: List[str]         # 错误信息
    warnings: List[str]       # 警告信息
```

---

### 5. 测试场景库 (scenarios/prompts.py)

**设计理念**：声明式配置

```python
@dataclass
class TestPrompt:
    id: str                   # 唯一标识
    label: str                # 显示名称
    description: str          # 场景描述
    messages: List[Dict]      # OpenAI 格式消息
    tags: List[str]           # 适用类别
    weight: int               # 权重 1-5
    expected_traits: List[str] # 期望特征
```

**场景覆盖**：
- 基础能力：通用对话、指令遵循
- 专业技能：代码生成、调试、数学推理
- 高级能力：逻辑推理、长上下文、智能体规划
- 创意任务：创意写作、翻译、摘要

**扩展性**：添加新场景只需在文件中定义新的 `TestPrompt` 对象并加入 `ALL_PROMPTS` 列表。

---

### 6. 报告生成器 (reporters/html_reporter.py)

**技术栈**：
- Jinja2 模板引擎（隐式使用字符串拼接）
- Canvas API（原生 JavaScript 绘图）
- 响应式 CSS Grid/Flexbox

**报告结构**：

```
HTML Report
├── Executive Summary (统计卡片)
├── Overall Rankings (排行榜 + 柱状图)
├── Per-Dimension Analysis (四维 Top 5)
├── Scenario Suitability Matrix (热力图)
├── Cost & Token Consumption (成本表)
└── Detailed Model Cards (可折叠详情)
```

**图表实现**：

```javascript
// 纯 Canvas 绘制柱状图，无外部依赖
function drawBars() {
    var canvas = document.getElementById('overallChart');
    var ctx = canvas.getContext('2d');
    
    // 计算布局
    // 绘制坐标轴
    // 绘制渐变柱状图
    // 添加标签
}
```

**设计特点**：
- ✅ 零外部依赖（单文件 HTML）
- ✅ 深色主题，护眼设计
- ✅ 响应式布局，支持移动端
- ✅ 交互式折叠/展开
- ✅ 颜色编码直观展示

---

### 7. Web 控制台 (web_ui.py)

**技术栈**：Python 内置 `http.server` 模块（零外部依赖）

**职责**：
- 提供基于浏览器的测试控制界面
- RESTful API 后端（模型列表、执行测试、状态轮询、报告查看）
- 后台线程执行测试，复用现有测试框架

**API 端点**：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | Web 控制台页面 |
| `/api/models` | GET | 从 NVIDIA API 获取所有模型 |
| `/api/run` | POST | 启动后台测试线程 |
| `/api/status` | GET | 实时查询测试进度 |
| `/api/report?path=...` | GET | 查看生成的 HTML 报告 |

**设计特点**：
- ✅ 单文件部署，零外部依赖
- ✅ 自包含 HTML（内嵌 CSS + JavaScript）
- ✅ 并发数实时校验（基于 NVIDIA 40 req/min 限制）
- ✅ 模型搜索过滤 + 分类快捷选择
- ✅ 预估 API 调用数和耗时

---

## 🔄 执行流程

### 主流程 (main.py)

```
1. 解析命令行参数
   ↓
2. 初始化配置
   ↓
3. Phase 1: 发现模型
   ├─ 调用 API 获取模型列表
   ├─ 分类和过滤
   └─ 显示统计信息
   ↓
4. Phase 2: 执行测试
   ├─ 创建测试器实例
   ├─ 并发执行测试（ThreadPoolExecutor）
   ├─ 实时显示进度
   └─ 收集结果到 result_map
   ↓
5. Phase 3: 生成报告
   ├─ 排序和聚合数据
   ├─ 生成 HTML 报告
   ├─ （可选）生成 JSON 报告
   └─ 显示控制台摘要
   ↓
6. 完成
```

### 并发测试机制

```python
with ThreadPoolExecutor(max_workers=concurrency) as pool:
    # 提交所有任务
    future_to_model = {
        pool.submit(tester.test_model, model): model
        for model in eligible_models
    }
    
    # 收集结果（按完成顺序）
    for future in as_completed(future_to_model):
        result = future.result()
        # 处理结果...
```

**优势**：
- ⚡ 充分利用 I/O 等待时间
- 🎯 动态负载均衡
- 🛡️ 异常隔离（单个失败不影响其他）

---

## 📊 评分算法详解

### 1. 可用性评分

```python
success_rate = success_count / total_attempts
score = success_rate  # 直接映射
passed = success_rate >= 0.5
```

### 2. 性能评分（加权综合）

```python
# 各维度归一化到 0-1
ttft_score = max(0.0, 1.0 - avg_ttft_ms / 10000)
latency_score = max(0.0, 1.0 - avg_total_ms / 30000)
throughput_score = min(1.0, avg_tokens_per_sec / 100)

# 加权平均
final_score = (
    ttft_score * 0.4 +      # TTFT 权重 40%
    latency_score * 0.3 +   # 延迟权重 30%
    throughput_score * 0.3  # 吞吐量权重 30%
)
```

### 3. 能力评分

```python
# 对每个场景进行评估
for scenario in scenarios:
    response = call_model(scenario.prompt)
    scenario_score = llm_judge(response, scenario.expected_traits)
    
# 加权平均（考虑场景权重）
total_weight = sum(s.weight for s in scenarios)
capability_score = sum(s.score * s.weight for s in scenarios) / total_weight
```

### 4. 综合评分

```python
overall_score = mean([
    availability_score,
    performance_score,
    capability_score,
    quality_score  # 如果启用
])
```

---

## 🎨 设计模式和最佳实践

### 1. 单一职责原则 (SRP)

每个模块只负责一个明确的功能：
- `scanner.py`：只负责模型发现和分类
- `api_client.py`：只负责 API 通信
- 每个 Tester：只负责一个测试维度

### 2. 开闭原则 (OCP)

- **对扩展开放**：轻松添加新测试维度
- **对修改封闭**：现有代码无需改动

```python
# 添加新测试只需：
class NewTester(BaseTester):
    def test_model(self, model):
        # 实现新逻辑
        pass

# 在 main.py 中注册
testers.append(NewTester(client))
```

### 3. 依赖注入

```python
class BaseTester:
    def __init__(self, client: Optional[NIMClient] = None):
        self.client = client or NIMClient()  # 支持注入或自建
```

**优势**：便于单元测试和 Mock

### 4. 数据类 (Dataclass)

使用 `@dataclass` 简化数据结构定义：

```python
@dataclass
class ModelInfo:
    id: str
    name: str
    category: str
    # ... 自动生成 __init__, __repr__ 等方法
```

### 5. 类型注解

全面使用类型提示，提高代码可读性和 IDE 支持：

```python
def test_model(self, model: ModelInfo) -> TestResult:
    ...
```

---

## 🔐 安全性考虑

### 1. API Key 管理

- ✅ 支持 `.env` 文件（不提交到版本控制）
- ✅ 环境变量优先级高于配置文件
- ⚠️ 不要硬编码 API Key

### 2. 错误处理

```python
try:
    resp = self.client.chat_completion(...)
except httpx.HTTPStatusError as e:
    errors.append(f"HTTP error: {e}")
except Exception as e:
    errors.append(f"Unexpected error: {e}")
```

### 3. 资源管理

使用上下文管理器确保资源释放：

```python
with httpx.Client(timeout=self.timeout) as client:
    resp = client.post(...)
# 自动关闭连接
```

---

## 🧪 测试策略

### 单元测试建议

```python
# tests/test_scanner.py
def test_classify_llm():
    category, tags = _classify("nvidia/llama-3-8b", "Llama 3")
    assert category == "llm"
    assert "text-generation" in tags

def test_classify_image():
    category, tags = _classify("stability/sdxl", "SDXL")
    assert category == "image"
```

### 集成测试

```python
# tests/test_api_client.py
def test_health_check():
    client = NIMClient()
    ok, elapsed = client.health_check()
    assert ok is True
    assert elapsed > 0
```

---

## 📈 性能优化

### 1. 并发控制

```python
# 根据 API 限流调整
CONCURRENCY = 5  # 默认适中值
```

### 2. 超时设置

```python
REQUEST_TIMEOUT = 120  # 避免长时间阻塞
```

### 3. 结果缓存（未来优化）

```python
# 可以考虑添加缓存层
from functools import lru_cache

@lru_cache(maxsize=100)
def get_model_info(model_id):
    ...
```

### 4. 懒加载

只在需要时生成报告，不在内存中保留所有中间结果。

---

## 🚀 扩展方向

### 1. 新增测试维度

```python
class SafetyTester(BaseTester):
    """测试模型的安全性和内容过滤"""
    
    def test_model(self, model):
        # 发送边界案例提示
        # 评估响应是否符合安全标准
        pass
```

### 2. 导出格式扩展

```python
class PDFReporter:
    """生成 PDF 格式报告"""
    
    def generate(self, data):
        # 使用 WeasyPrint 或 ReportLab
        pass
```

### 3. Web Dashboard

```python
# 使用 FastAPI + React 构建实时监控面板
@app.get("/api/results")
def get_results():
    return load_results()
```

### 4. 历史对比

```python
# 存储历史测试结果
# 生成趋势图和对比报告
def compare_runs(run1_id, run2_id):
    ...
```

---

## 📚 技术栈总结

| 组件 | 技术 | 用途 |
|------|------|------|
| HTTP 客户端 | httpx | API 通信，支持同步/异步 |
| 配置管理 | Pydantic Settings | 类型安全的配置 |
| 数据处理 | Python Dataclasses | 结构化数据 |
| 并发 | ThreadPoolExecutor | 多线程并发测试 |
| 报告生成 | 原生 HTML/CSS/JS | 零依赖报告 |
| 图表 | Canvas API | 轻量级图表绘制 |
| 模板 | 字符串格式化 | 简单高效的模板 |

---

## 🎓 学习要点

通过本项目可以学习：

1. **API 客户端设计**：封装 RESTful API，处理认证和错误
2. **测试框架架构**：可扩展的测试系统设计
3. **并发编程**：ThreadPoolExecutor 实战应用
4. **配置管理**：Pydantic Settings 最佳实践
5. **报告生成**：自包含 HTML 报告技巧
6. **数据可视化**：Canvas API 基础绘图
7. **设计模式**：策略模式、工厂模式应用
8. **代码组织**：模块化设计和职责分离

---

**架构设计核心理念**：简洁、可扩展、易维护 🎯
