# Quick Start Guide

**Language / 语言**: [🇺🇸 English](QUICKSTART.md) | [🇨🇳 中文](QUICKSTART_ZH.md)

---

## ⚡ Get Started in 5 Minutes

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Configure API Key

Create `.env` file:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` and fill in your NVIDIA API Key:

```env
NVIDIA_API_KEY="nvapi-your-key-here"
```

> 💡 Get API Key: Visit [build.nvidia.com](https://build.nvidia.com) to register and create a key

### 3️⃣ Run Tests

```bash
# Quick test (3 models per category)
python main.py --scope sample

# Or test all models
python main.py
```

### 4️⃣ View Report

After testing completes, open the HTML report in the `output/` directory:

```bash
# Windows
start output\nvidia_report_*.html

# Mac
open output/nvidia_report_*.html

# Linux
xdg-open output/nvidia_report_*.html
```

---

## 🎯 Common Use Cases

### Test Only LLM Models

```bash
python main.py --scope llm --concurrency 10
```

### Skip Quality Evaluation (Faster)

```bash
python main.py --no-quality
```

### High Concurrency Testing

```bash
python main.py --concurrency 20 --scope sample
```

### Limit Number of Models

```bash
python main.py --max-models 15
```

### Custom Output Directory

```bash
python main.py --output ./my_results
```

---

## 📊 Understanding Results

### Console Output

You'll see real-time progress:
- ✅ Green: Test passed
- ❌ Red: Test failed
- Score: 0.000 - 1.000 (higher is better)

### HTML Report Sections

1. **Executive Summary**: Key statistics at a glance
2. **Overall Rankings**: Top models with bar charts
3. **Per-Dimension Analysis**: Best models in each category
4. **Scenario Suitability Matrix**: Heatmap of model performance
5. **Cost Analysis**: Token usage and estimated costs
6. **Detailed Model Cards**: Expandable details for each model

---

## 🔧 Troubleshooting

### "API Key not set" Error

```bash
# Check if .env file exists
ls -la .env

# Verify content
cat .env

# Or set environment variable directly
export NVIDIA_API_KEY="nvapi-your-key"
```

### Timeout Errors

```bash
# Reduce concurrency
python main.py --concurrency 3

# Increase timeout (in config.py or .env)
NV_TEST_REQUEST_TIMEOUT=180
```

### Rate Limiting (429 Error)

```bash
# Lower concurrency
python main.py --concurrency 2

# Test in smaller batches
python main.py --scope llm --max-models 10
```

---

## 💡 Pro Tips

1. **Start with sample mode** to quickly understand the framework
2. **Use `--no-quality`** for faster initial tests
3. **Adjust concurrency** based on your API rate limits
4. **Check HTML reports** in browser for interactive visualizations
5. **Use JSON output** for programmatic analysis (`REPORT_FORMAT=json`)

---

## 📚 Next Steps

- Read the full [README](README_EN.md) for detailed documentation
- Explore [ARCHITECTURE](ARCHITECTURE_EN.md) to understand the codebase
- Check [CONTRIBUTING](CONTRIBUTING_EN.md) to contribute to the project

---

[🇨🇳 中文版](QUICKSTART_ZH.md) | [🇺🇸 English](QUICKSTART.md)
