# 快速开始指南

**Language / 语言**: [🇨🇳 中文](QUICKSTART_ZH.md) | [🇺🇸 English](QUICKSTART.md)

---

## ⚡ 5分钟上手

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 2️⃣ 配置 API Key

创建 `.env` 文件：

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

编辑 `.env`，填入你的 NVIDIA API Key：

```env
NVIDIA_API_KEY="nvapi-your-key-here"
```

> 💡 获取 API Key：访问 [build.nvidia.com](https://build.nvidia.com) 注册并创建密钥

### 3️⃣ 运行测试

```bash
# 快速测试（每个类别3个模型）
python main.py --scope sample

# 或测试所有模型
python main.py

# 指定具体模型测试
python main.py --models "meta/llama-3.2-11b-vision-instruct,01-ai/yi-large"

# 只测试可用性和延迟
python main.py --models "meta/llama-3.2-11b-vision-instruct" --tests availability,performance
```

> 💡 也可使用 Web 浏览器控制台：
> ```bash
> python web_ui.py --port 8080
> # 打开 http://127.0.0.1:8080
> ```

### 4️⃣ 查看报告

测试完成后，在 `output/` 目录打开 HTML 报告：

```bash
# Windows
start output\nvidia_report_*.html

# Mac
open output/nvidia_report_*.html

# Linux
xdg-open output/nvidia_report_*.html
```

---

## 🎯 常用命令

```bash
# 只测试 LLM 模型
python main.py --scope llm

# 提高并发速度（10个线程）
python main.py --concurrency 10

# 跳过耗时的质量测试
python main.py --no-quality

# 指定输出目录
python main.py --output ./my_results

# 指定具体模型
python main.py --models "nvidia/llama-3.3-nemotron-super-49b-v1,nvidia/mistral-large"

# 只运行指定测试维度（可用性+延迟）
python main.py --models "meta/llama-3.2-11b-vision-instruct" --tests availability,performance

# 组合使用：快速测试LLM，高并发
python main.py --scope llm --concurrency 10 --no-quality
```

### 使用 Web 浏览器控制台

```bash
# 启动 Web 界面
python web_ui.py --port 8080

# 浏览器打开 http://127.0.0.1:8080
# 功能：模型下拉多选、并发数校验建议、测试维度勾选、实时进度、在线查看报告
```

---

## 📊 理解测试结果

### 评分标准

- **1.0 (100%)**：完美表现
- **0.8-0.9**：优秀
- **0.6-0.8**：良好
- **0.4-0.6**：一般
- **< 0.4**：较差

### 四个测试维度

1. **可用性** (Availability)：模型是否能正常访问和响应
2. **性能** (Performance)：响应速度和吞吐量
3. **能力** (Capability)：各种场景下的实际表现
4. **质量** (Quality)：输出质量和可靠性（可选）

### 如何选择模型？

- **追求速度** → 查看"性能 Top 5"
- **代码任务** → 查看场景矩阵的 "Code Generation" 列
- **综合最佳** → 查看总体排名 Top 3
- **成本敏感** → 查看成本和 Token 消耗表

---

## ❓ 常见问题

### Q: 测试需要多长时间？

A: 取决于模型数量和并发数：
- 采样模式（~15个模型）：5-10分钟
- 全部模型（~150个）：30-60分钟

### Q: 如何加快测试速度？

A: 
```bash
# 方法1：增加并发数
python main.py --concurrency 15

# 方法2：跳过质量测试
python main.py --no-quality

# 方法3：只测试部分模型
python main.py --scope sample --max-models 20
```

### Q: 遇到 429 错误怎么办？

A: 降低并发数：
```bash
python main.py --concurrency 3
```

### Q: 可以自定义测试内容吗？

A: 可以！编辑 `scenarios/prompts.py` 添加你自己的测试场景。

---

## 🚀 下一步

- 📖 阅读完整的 [README_ZH.md](README_ZH.md) 了解详细功能
- 🔧 查看 `config.py` 了解所有配置选项
- 📝 自定义测试场景：编辑 `scenarios/prompts.py`

---

**开始测试吧！** 🎉
