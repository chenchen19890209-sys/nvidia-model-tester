# NVIDIA Model Tester

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Language / 语言**: [🇺🇸 English](README.md) | [🇨🇳 中文](README_ZH.md)

---

A comprehensive automated testing framework for evaluating and comparing AI models available through the NVIDIA NIM API.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env with your NVIDIA_API_KEY

# Run tests
python main.py --scope sample
```

## 📚 Documentation

All documentation is organized in the [`docs/`](docs/) directory:

### Quick Links
- **[📖 Documentation Index](docs/DOCS_INDEX_EN.md)** - Navigate all documents
- **[⚡ Quick Start](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[📘 Full Guide](docs/README.md)** - Comprehensive documentation
- **[🏗️ Architecture](docs/ARCHITECTURE.md)** - Technical details
- **[🤝 Contributing](docs/CONTRIBUTING.md)** - How to contribute

### Language Support
All documents are available in both **English** and **Chinese** (中文). Each document has a language toggle link at the top.

## ✨ Features

- 🔍 **Automatic Model Discovery** - Fetch and classify all available models
- 🧪 **Multi-dimensional Testing** - Availability, Performance, Capability, Quality
- ⚡ **Concurrent Execution** - Configurable concurrency with rate limiting
- 📊 **Visual Reports** - Interactive HTML reports with charts and heatmaps
- 💰 **Cost Analysis** - Token usage tracking and cost estimation
- 🌐 **Bilingual Support** - English and Chinese documentation

## 📋 Requirements

- Python 3.8+
- NVIDIA API Key (from [build.nvidia.com](https://build.nvidia.com))

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🔗 Links

- [NVIDIA NIM API](https://docs.nvidia.com/nim/)
- [Build Portal](https://build.nvidia.com)

---

**Happy Testing!** 🎉
