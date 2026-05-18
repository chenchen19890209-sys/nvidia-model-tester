# NVIDIA Model Tester - 项目说明文档

**Language / 语言**: [🇨🇳 中文](README_ZH.md) | [🇺🇸 English](README.md)

---

## 📖 项目概述

**NVIDIA Model Tester** 是一个功能强大的自动化测试框架，专门用于评估和比较 NVIDIA NIM API 提供的各种 AI 模型。它能够自动发现、分类和测试所有可用的模型，并生成详细的 HTML 报告，帮助用户选择最适合其应用场景的模型。

### 核心功能

- 🔍 **自动模型发现**：从 NVIDIA API 自动获取所有可用模型列表
- 🏷️ **智能分类**：根据模型特性自动分类（LLM、多模态、图像、音频、专用模型）
- 🧪 **多维度测试**：可用性、性能、能力、质量四个维度全面评估
- 📊 **可视化报告**：生成精美的交互式 HTML 报告，包含排名、图表和详细分析
- ⚡ **并发测试**：支持多线程并发测试，大幅提升测试效率
- 💰 **成本估算**：基于 token 使用量估算调用成本

---

## 🏗️ 项目架构

```
nvidia-model-tester/
├── main.py                  # 主程序入口，协调测试流程
├── config.py                # 配置管理，使用 Pydantic Settings
├── requirements.txt         # Python 依赖包
├── .env.example            # 环境变量示例文件
│
├── models/                  # 模型管理模块
│   ├── scanner.py          # 模型发现和分类器
│   └── registry.py         # 模型注册表
│
├── tests/                   # 测试套件模块
│   ├── base.py             # 测试基类和结果数据结构
│   ├── availability.py     # 可用性测试
│   ├── performance.py      # 性能测试
│   ├── capability.py       # 能力测试
│   └── quality.py          # 质量评估测试
│
├── scenarios/              # 测试场景模块
│   └── prompts.py          # 预定义的测试提示词库
│
├── reporters/              # 报告生成模块
│   └── html_reporter.py    # HTML 报告生成器
│
├── utils/                  # 工具模块
│   ├── api_client.py       # NVIDIA API 客户端
│   └── metrics.py          # 指标计算工具
│
└── output/                 # 输出目录（自动生成）
    └── *.html              # 生成的测试报告
```

---

## 🚀 快速开始

### 1. 环境准备

#### 系统要求
- Python 3.8 或更高版本
- NVIDIA API Key（从 [build.nvidia.com](https://build.nvidia.com) 获取）

#### 安装依赖

```bash
# 克隆或下载项目后，进入项目目录
cd nvidia-model-tester

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

有两种方式配置 NVIDIA API Key：

#### 方式一：使用 .env 文件（推荐）

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
nano .env  # 或使用你喜欢的编辑器
```

在 `.env` 文件中设置：
```env
NVIDIA_API_KEY="nvapi-your-api-key-here"
```

#### 方式二：使用环境变量

```bash
# Windows PowerShell
$env:NVIDIA_API_KEY="nvapi-your-api-key-here"

# Linux/Mac
export NVIDIA_API_KEY="nvapi-your-api-key-here"
```

### 3. 运行测试

#### 基础用法

```bash
# 测试所有发现的模型
python main.py

# 仅测试 LLM 模型
python main.py --scope llm

# 测试每个类别的 3 个样本模型（快速模式）
python main.py --scope sample

# 自定义并发数（提高速度）
python main.py --concurrency 10

# 指定输出目录
python main.py --output ./my_reports

# 跳过质量评估（节省时间）
python main.py --no-quality
```

#### 命令行参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--scope` | 测试范围：all, llm, multimodal, image, audio, specialized, sample | all |
| `--max-models` | 限制测试模型数量 | 无限制 |
| `--concurrency` | 最大并发请求数（1-50） | 5 |
| `--output` | 报告输出目录 | ./output |
| `--no-quality` | 跳过质量评估测试 | 启用质量评估 |
| `--api-key` | 直接传入 API Key | 从环境变量读取 |

---

## 🧪 测试维度详解

项目提供四个维度的测试，每个维度关注不同的模型特性：

### 1. 可用性测试 (Availability)

**目的**：验证模型端点是否可访问且响应正常

**测试内容**：
- API 健康检查
- 最小化聊天完成测试（发送简单请求）
- 一致性验证（多次请求确保稳定性）

**评分标准**：
- 成功率 ≥ 50% 视为通过
- 分数 = 成功次数 / 总尝试次数

**适用模型**：所有聊天模型（LLM、多模态）

### 2. 性能测试 (Performance)

**目的**：测量模型的响应速度和吞吐量

**测试内容**：
- **TTFT** (Time To First Token)：首字延迟，衡量用户感知的响应速度
- **总延迟**：完整响应所需时间
- **吞吐量**：每秒生成的 token 数

**评分算法**（加权综合）：
```
总分 = TTFT得分×40% + 延迟得分×30% + 吞吐量得分×30%

TTFT得分：
  < 500ms  → 1.0
  > 10000ms → 0.0
  线性插值

延迟得分：
  < 5000ms  → 1.0
  > 30000ms → 0.0
  线性插值

吞吐量得分：
  > 100 tok/s → 1.0
  < 5 tok/s   → 0.0
  线性插值
```

**重复测试**：默认执行 3 次取平均值，确保结果稳定

### 3. 能力测试 (Capability)

**目的**：评估模型在各种实际场景中的表现

**测试场景库**（12 个场景）：

| 场景 ID | 名称 | 描述 | 权重 |
|---------|------|------|------|
| general_chat | 通用对话 | 基本指令遵循和常识问答 | 3 |
| code_generation | 代码生成 | 编写复杂函数 | 5 |
| code_debugging | 代码调试 | 识别和修复代码错误 | 4 |
| math_reasoning | 数学推理 | 多步数学问题求解 | 4 |
| logical_reasoning | 逻辑推理 | 约束条件下的复杂推理 | 5 |
| creative_writing | 创意写作 | 生成富有创意的文本 | 2 |
| summarization | 文本摘要 | 浓缩长文本保留关键信息 | 3 |
| translation | 翻译 | 英译中准确性测试 | 2 |
| agentic_reasoning | 智能体规划 | 多步骤工具使用规划 | 4 |
| long_context | 长上下文理解 | 从长文档中提取信息 | 3 |
| multimodal_understanding | 多模态理解 | 空间理解和详细描述 | 2 |
| instruction_following | 约束指令遵循 | 精确遵循格式和内容约束 | 4 |

**评分方法**：
- 使用 LLM-as-Judge 方法，用强参考模型评估回答质量
- 对比预期特征（如"准确"、"清晰"、"逐步推理"等）
- 综合各场景得分得出能力总分

### 4. 质量评估 (Quality)

**目的**：深度评估模型输出的质量和可靠性

**测试方法**：
- 使用高质量参考模型（默认：`nvidia/llama-3.3-nemotron-super-49b-v1`）作为裁判
- 对模型回答进行细粒度评分
- 评估回答的相关性、准确性、完整性

**注意**：此测试耗时较长，可通过 `--no-quality` 参数跳过

---

## 📊 报告解读

测试完成后，会在 `output/` 目录生成 HTML 报告，文件名格式：`nvidia_report_YYYYMMDD_HHMMSS.html`

### 报告结构

#### 1. 执行摘要 (Executive Summary)

展示关键统计数据：
- 测试模型总数
- 覆盖的类别数
- 全部测试通过的模型数
- 平均得分
- 最佳模型

#### 2. 总体排名 (Overall Rankings)

- **柱状图**：直观展示前 20 名模型的综合得分
- **排行榜表格**：
  - 排名
  - 模型 ID 和类别
  - 综合得分（带进度条）
  - 各维度测试结果标签（绿色=通过，红色=失败）

#### 3. 分维度分析 (Per-Dimension Analysis)

分别展示四个维度的 Top 5 模型：
- 可用性 Top 5
- 性能 Top 5
- 能力 Top 5
- 质量 Top 5

帮助识别在特定方面表现优异的模型。

#### 4. 场景适用性矩阵 (Scenario Suitability Matrix)

热力图形式展示各模型在不同场景的表现：
- 行：模型（Top 20）
- 列：测试场景
- 颜色编码：
  - 🟢 深绿：0.8-1.0（优秀）
  - 🟡 黄色：0.6-0.8（良好）
  - 🟠 橙色：0.4-0.6（一般）
  - 🔴 红色：< 0.4（较差）

**用途**：快速找到适合特定应用场景的模型

#### 5. 成本和 Token 消耗 (Cost & Token Consumption)

估算每个模型的调用成本：
- 总 Token 数
- Prompt Token 数（输入）
- Completion Token 数（输出）
- 预估费用（美元）

**成本计算公式**：
```
费用 = (输入Token/1000 × $0.0001) + (输出Token/1000 × $0.0004)
```

*注：费率可在配置中自定义*

#### 6. 详细模型卡片 (Detailed Model Cards)

每个模型的详细信息，可折叠展开：
- 模型基本信息（ID、类别、综合得分）
- 各维度测试结果和详细指标
- 错误信息（如果有）

**点击模型名称可展开/收起详情**

---

## ⚙️ 配置详解

配置文件位于 `config.py`，使用 Pydantic Settings 管理，支持环境变量覆盖。

### 主要配置项

```python
# API 配置
NVIDIA_API_KEY: str           # API Key（必需）
NVIDIA_API_BASE: str          # API 基础 URL（默认：https://integrate.api.nvidia.com/v1）

# 测试范围
TEST_SCOPE: TestScope         # 测试范围枚举（all/llm/multimodal/image/audio/specialized/sample）
MAX_MODELS: Optional[int]     # 最大测试模型数（None=全部）
CONCURRENCY: int              # 并发数（1-50，默认 5）
REQUEST_TIMEOUT: int          # 请求超时秒数（默认 120）

# 测试参数
TEST_REPEAT: int              # 每个测试重复次数（1-10，默认 3）
MAX_TOKENS_GENERATE: int      # 生成任务最大 token 数（默认 512）
MAX_TOKENS_LONG_CONTEXT: int  # 长上下文测试最大 token 数（默认 4096）

# 输出配置
OUTPUT_DIR: str               # 输出目录（默认 ./output）
REPORT_FORMAT: ReportFormat   # 报告格式（html/json/both，默认 both）
REPORT_TITLE: str             # 报告标题

# 成本估算
COST_PER_1K_INPUT_TOKENS: float   # 每千输入 token 成本（默认 $0.0001）
COST_PER_1K_OUTPUT_TOKENS: float  # 每千输出 token 成本（默认 $0.0004）

# 质量评估
QUALITY_REFERENCE_MODEL: str      # 参考模型（默认 llama-3.3-nemotron-super-49b-v1）
ENABLE_QUALITY_EVAL: bool         # 是否启用质量评估（默认 True）
```

### 使用环境变量覆盖配置

所有配置项都可以通过环境变量覆盖，环境变量前缀为 `NV_TEST_`：

```bash
# 示例
export NV_TEST_CONCURRENCY=10
export NV_TEST_TEST_SCOPE=llm
export NV_TEST_OUTPUT_DIR=./my_output
export NV_TEST_ENABLE_QUALITY_EVAL=false
```

---

## 🔧 高级用法

### 自定义测试场景

编辑 `scenarios/prompts.py` 添加新的测试场景：

```python
MY_CUSTOM_SCENARIO = TestPrompt(
    id="my_scenario",
    label="我的自定义场景",
    description="场景描述",
    messages=[
        {"role": "user", "content": "你的测试提示词"}
    ],
    tags=["llm"],  # 适用的模型类别
    weight=4,      # 权重 1-5
    expected_traits=["accurate", "detailed"],  # 期望的回答特征
)

# 添加到 ALL_PROMPTS 列表
ALL_PROMPTS.append(MY_CUSTOM_SCENARIO)
```

### 扩展测试维度

创建新的测试类需要继承 `BaseTester`：

```python
from tests.base import BaseTester, TestResult
from models.scanner import ModelInfo

class MyCustomTester(BaseTester):
    def name(self) -> str:
        return "my_test"
    
    def description(self) -> str:
        return "我的自定义测试描述"
    
    def test_model(self, model: ModelInfo) -> TestResult:
        # 实现测试逻辑
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

然后在 `main.py` 中注册：

```python
testers.append(MyCustomTester(client))
```

### 批量测试不同配置

```bash
# 测试不同并发数的性能影响
for concurrency in 1 5 10 20; do
    python main.py --scope sample --concurrency $concurrency --output "./results/conc_$concurrency"
done
```

---

## 📈 性能优化建议

### 1. 调整并发数

- **低并发（1-3）**：适合测试少量关键模型，避免 API 限流
- **中等并发（5-10）**：平衡速度和稳定性，推荐默认值
- **高并发（10-50）**：快速测试大量模型，但可能触发速率限制

### 2. 使用采样模式

```bash
# 快速了解各类别代表模型
python main.py --scope sample --concurrency 10
```

### 3. 跳过耗时测试

```bash
# 跳过质量评估（最耗时的测试）
python main.py --no-quality
```

### 4. 限制模型数量

```bash
# 只测试前 20 个模型
python main.py --max-models 20
```

### 5. 针对特定类别测试

```bash
# 只测试 LLM 模型
python main.py --scope llm

# 只测试多模态模型
python main.py --scope multimodal
```

---

## 🐛 故障排除

### 常见问题

#### 1. API Key 未设置

**错误信息**：
```
WARNING: NVIDIA_API_KEY is not set.
❌ Failed to discover models: 401 Unauthorized
```

**解决方案**：
```bash
# 检查环境变量
echo $NVIDIA_API_KEY  # Linux/Mac
echo $env:NVIDIA_API_KEY  # Windows

# 或在 .env 文件中正确配置
```

#### 2. 请求超时

**错误信息**：
```
httpx.ReadTimeout: timed out
```

**解决方案**：
```bash
# 增加超时时间
export NV_TEST_REQUEST_TIMEOUT=180

# 或降低并发数减少服务器压力
python main.py --concurrency 3
```

#### 3. 速率限制

**错误信息**：
```
429 Too Many Requests
```

**解决方案**：
```bash
# 降低并发数
python main.py --concurrency 2

# 分批测试
python main.py --scope llm --max-models 10
```

#### 4. 模型不可用

某些模型可能在测试时暂时不可用，这是正常现象。报告会标记这些模型的可用性测试失败。

#### 5. 内存不足

测试大量模型时可能占用较多内存：

**解决方案**：
```bash
# 减少并发数
python main.py --concurrency 3

# 或分批测试
python main.py --scope llm
python main.py --scope multimodal
```

---

## 📝 输出示例

### 控制台输出

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

### HTML 报告

打开生成的 HTML 文件，您将看到：
- 深色主题的现代化界面
- 交互式柱状图和热力图
- 可折叠的模型详情卡片
- 响应式设计，支持移动端查看

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出改进建议！

### 开发环境设置

```bash
# 克隆仓库
git clone <repository-url>
cd nvidia-model-tester

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest black flake8
```

### 代码规范

- 遵循 PEP 8 风格指南
- 使用类型注解
- 编写清晰的文档字符串
- 保持函数单一职责

### 提交 Pull Request

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 🔗 相关链接

- [NVIDIA NIM API 文档](https://docs.nvidia.com/nim/)
- [NVIDIA Build Portal](https://build.nvidia.com)
- [OpenAI API 兼容接口](https://platform.openai.com/docs/api-reference)

---

## 📞 支持与反馈

如有问题或建议，请：
1. 查阅本文档的故障排除部分
2. 查看 GitHub Issues
3. 提交新的 Issue 描述您的问题

---

**祝您测试愉快！** 🚀
