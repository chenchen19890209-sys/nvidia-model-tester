# NVIDIA Model Tester

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Language / 语言**: [🇨🇳 中文](README_ZH.md) | [🇺🇸 English](README.md)

---

一个功能强大的自动化测试框架，用于评估和比较 NVIDIA NIM API 提供的各种 AI 模型。

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 文件，填入你的 NVIDIA_API_KEY

# 运行测试
python main.py --scope sample
```

## 📚 文档

所有文档都组织在 [`docs/`](docs/) 目录中：

### 快速链接
- **[📖 文档索引](docs/DOCS_INDEX.md)** - 浏览所有文档
- **[⚡ 快速开始](docs/QUICKSTART_ZH.md)** - 5分钟上手指南
- **[📘 完整指南](docs/README_ZH.md)** -  comprehensive 用户手册
- **[🏗️ 技术架构](docs/ARCHITECTURE_ZH.md)** - 系统设计和实现细节
- **[🤝 贡献指南](docs/CONTRIBUTING_ZH.md)** - 如何参与项目开发

### 语言支持
所有文档都提供**英文**和**中文**版本。每个文档顶部都有语言切换链接。

## ✨ 主要特性

- 🔍 **自动模型发现** - 自动获取并分类所有可用模型
- 🧪 **多维度测试** - 可用性、性能、能力、质量四个维度全面评估
- ⚡ **并发执行** - 可配置的并发数，内置速率限制
- 📊 **可视化报告** - 交互式 HTML 报告，包含图表和热力图
- 💰 **成本分析** - Token 用量跟踪和成本估算
- 🌐 **双语支持** - 完整的英文和中文文档

## 📋 系统要求

- Python 3.8 或更高版本
- NVIDIA API Key（从 [build.nvidia.com](https://build.nvidia.com) 获取）

## 📄 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [NVIDIA NIM API 文档](https://docs.nvidia.com/nim/)
- [NVIDIA Build Portal](https://build.nvidia.com)

---

**祝您测试愉快！** 🎉
