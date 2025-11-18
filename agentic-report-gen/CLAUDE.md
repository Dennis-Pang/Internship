# 多 Agent 医疗报告生成系统 —— 需求总结（给 Codex 使用）

## 1. 系统总体目标
构建一个多 Agent 医疗报告生成系统，在本地私有环境中运行 DeepSeek R1（671B）用于医疗数据整合与报告生成。

特点包括：

- 强隐私：模型与数据全部在私有服务器
- 架构：主 Agent + 多个子 Agent（sub-agents）
- 功能：从多类型医疗数据抽取结构化信息
- 特性：子 Agent 可并行调用
- 平台：不使用 LangChain / LangGraph
- 观测性：使用 Langfuse（自托管）
- 技术：原生 Python + OpenAI/DeepSeek 兼容 API

---

## 2. 输入数据类型
系统需处理多模态医疗数据，包括：

### 2.1 表格类（Tabular）
- CSV、XLSX、SQL 查询结果
这部分数据暂时没有，逻辑可以空着

### 2.2 传感器类（Sensor）
- 时间序列数据（血糖 CGM、心率、步态等）
这部分数据暂时没有，逻辑可以空着

### 2.3 文本 / PDF（OCR 后）
- 出院小结、影像报告、手术记录
- 非结构化医疗文本
这部分pdf2markdown已经做好了。/home/user/ai_agent/ai_agent_project/agentic-report-gen/pdf_to_markdown.py可以让sub agent直接调用这个脚本获取数据，之后数据再处理的部分可以逻辑暂时空着
---

## 3. 系统组件（模块划分）

### 3.1 主 Agent（Main Agent）
基于 DeepSeek R1，通过 CoT 执行三个核心任务：

1. 根据用户请求与可用文件 → 生成 `PLAN_JSON`
2. 决定需要调用哪些子 Agent
3. 输入所有子 Agent 的结构化结果 → 生成 `FINAL_REPORT`

主 Agent 不直接读取任何原始文件，只使用子 Agent 输出的 JSON。

---

### 3.2 子 Agent（Sub-Agents）
每个子 Agent 独立处理特定类型的数据，并输出结构化 JSON。

#### A. Tabular Agent

#### B. Sensor Agent

#### C. PDF/Text Agent


### 3.3 调度器（Orchestrator）
由 Python 控制，职责包括：

- 调用主 Agent 获取 `PLAN_JSON`
- 根据计划激活对应子 Agent
- 使用 `asyncio.gather` 并行调用子 Agent
- 合并子 Agent 输出的 JSON
- 将结构化结果传回主 Agent，让其生成报告
- 处理错误、时间控制、上下文流转

无任何 LangChain，全部原生实现。

---

### 3.4 可观测性层（Langfuse）
整个流水线必须将以下内容写入 Langfuse（自托管）：

- 一条完整任务 = 一个 Trace
- 主 Agent 规划、每个子 Agent、最终报告生成 = 独立 Span

每个 Span 记录：

- 输入（可脱敏）
- 输出（可脱敏）
- 耗时
- 状态（success / error）
- metadata（模型版本、报告类型等）

---

## 4. 系统执行流程

### Step 1：用户请求
输入包含：

- 用户自然语言需求
- 医疗数据引用（tabular / sensor / pdf）

### Step 2：主 Agent（Planning 阶段）
主 Agent 输出一个 JSON 计划，例如：

  {
    "need_tabular": true,
    "need_sensor": false,
    "need_pdf": true
  }

### Step 3：并行调用子 Agent
根据 `PLAN_JSON`：

- 并行运行 Tabular / Sensor / PDF 子 Agent
- 每个子 Agent 返回结构化 JSON
- 调度器合并为 unified JSON，例如：

  {
    "labs": [...],
    "vitals": [...],
    "sensor_summary": {...},
    "past_reports": [...],
    "problems": [...]
  }

### Step 4：主 Agent 生成最终报告
主 Agent 基于结构化数据输出 `FINAL_REPORT`：

- 不得编造不存在的事实
- 缺失信息必须明确说明（例如“未见相关记录”）
- 输出自然语言医疗报告草稿

### Step 5：返回报告
输出报告草稿用于后续审查或存档。

---

## 5. 技术要求

### 5.1 不使用 LangChain / LangGraph
所有 agent 调度、并行、数据流控制以原生 Python 实现。

### 5.2 模型调用
- DeepSeek 使用 OpenAI-Compatible API（`/v1/chat/completions`）
- 可用官方 SDK 或简单 HTTP 客户端

### 5.3 并行要求
- 使用 `asyncio.gather`
- 子 Agent 并行
- 主 Agent 顺序执行

### 5.4 数据格式
所有中间结果必须为 JSON：

- `PLAN_JSON`
- 子 Agent 输出
- unified JSON
- 最终报告文本

---

## 6. 扩展（可选）
未来可扩展：

- Reviewer Agent（审查报告一致性）
- 自动评估（LLM-as-judge）
- 医生修改 diff 用于改进模型
- 更多类型子 Agent

---

