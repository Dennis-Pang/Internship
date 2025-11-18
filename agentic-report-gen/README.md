# 多 Agent 医疗报告生成系统

基于 DeepSeek R1 的多 Agent 医疗报告生成系统，支持从 PDF 等医疗数据源生成综合报告。

## 快速开始

### 1. 安装依赖

```bash
pip install openai loguru python-dotenv langfuse
```

### 2. 配置 API

```bash
cp .env.example .env
# 编辑 .env，设置 DEEPSEEK_API_BASE 和 DEEPSEEK_API_KEY
```

### 3. 运行

```bash
python main.py --request "生成患者报告" --pdf data/pdf/report.pdf --print
```

## 系统架构

```
用户请求 → 主Agent(Planning) → 并行调用子Agent → 合并数据 → 主Agent(Report) → 输出报告
```

**子 Agent:**
- ✅ PDF Agent (完整实现)
- 🚧 Tabular Agent (placeholder)
- 🚧 Sensor Agent (placeholder)

## 项目结构

```
agentic-report-gen/
├── agent.py           # 核心 Agent 系统
├── main.py            # CLI 入口
├── prompts/           # 提示词目录
├── tools/             # 工具脚本
│   └── pdf_to_markdown.py
├── data/              # 数据目录
│   ├── pdf/
│   └── markdown/
├── output/            # 输出目录
└── .env.example       # 环境变量模板
```

## 使用示例

```bash
# 单个 PDF
python main.py --request "生成综合报告" --pdf report.pdf

# 多个 PDF
python main.py --request "分析所有文档" --pdf file1.pdf file2.pdf file3.pdf

# 详细日志
python main.py --request "分析" --pdf report.pdf --verbose

# 自定义输出目录
python main.py --request "报告" --pdf report.pdf -o ./my_reports
```

## 作为库使用

```python
import asyncio
from agent import generate_medical_report

result = asyncio.run(generate_medical_report(
    user_request="生成患者报告",
    pdf_files=["report.pdf"]
))

print(result['final_report'])
```

## 环境变量

```bash
# DeepSeek API
DEEPSEEK_API_BASE=http://localhost:8000/v1
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_MODEL=deepseek-reasoner

# Langfuse (可选)
LANGFUSE_ENABLED=false

# 模型参数
TEMPERATURE=0.7
MAX_TOKENS=4096
```

## 输出

系统生成两个文件:
- `report_TIMESTAMP.json` - 完整结果（计划、结构化数据、报告）
- `report_TIMESTAMP.md` - 纯报告文本

## 技术特点

- 原生 Python + asyncio (无 LangChain)
- 并行处理 (asyncio.gather)
- 提示词与代码分离
- OpenAI-Compatible API
- 可选 Langfuse 观测性

## 详细说明

查看 `CLAUDE.md` 了解完整需求和实现细节。
