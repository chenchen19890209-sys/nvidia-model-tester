"""按场景组织的测试提示词。

每个场景包含：
- id: 唯一标识符
- label: 人类可读的名称
- description: 此场景评估的内容
- messages: 聊天消息列表（OpenAI 格式）
- tags: 适用的模型类别
- weight: 总体评分的重要性权重（1-5）
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TestPrompt:
    """测试提示词数据类。
    
    Attributes:
        id: 唯一标识符
        label: 人类可读的名称
        description: 此场景评估的内容
        messages: 聊天消息列表
        tags: 适用的模型类别
        weight: 重要性权重（1-5）
        expected_traits: 期望的特性列表
        reference_answer: 参考答案
    """
    id: str
    label: str
    description: str
    messages: list[dict[str, str]]
    tags: list[str] = field(default_factory=lambda: ["llm"])
    weight: int = 3
    expected_traits: list[str] = field(default_factory=list)
    reference_answer: Optional[str] = None
    label_zh: str = ""


# ── Scenario: General Knowledge & Instruction Following ──────

GENERAL_CHAT = TestPrompt(
    id="general_chat",
    label="General Chat & Instruction",
    label_zh="通用对话与指令",
    description="Basic instruction following and general knowledge",
    messages=[
        {
            "role": "user",
            "content": (
                "Explain the concept of 'attention mechanism' in transformer "
                "architectures in simple terms. Include why it is important "
                "for modern AI."
            ),
        }
    ],
    tags=["llm", "multimodal"],
    weight=3,
    expected_traits=["clear", "accurate", "well-structured"],
)

# ── Scenario: Code Generation ─────────────────────────────────

CODE_GENERATION = TestPrompt(
    id="code_generation",
    label="Code Generation",
    label_zh="代码生成",
    description="Write a non-trivial function from a description",
    messages=[
        {
            "role": "user",
            "content": (
                "Write a Python function `merge_intervals(intervals: list[tuple[int, int]]) "
                "-> list[tuple[int, int]]` that merges overlapping intervals. "
                "Include type hints, a docstring, and at least 3 test cases.\n\n"
                "Example:\n  Input: [(1,3),(2,6),(8,10),(15,18)]\n"
                "  Output: [(1,6),(8,10),(15,18)]"
            ),
        }
    ],
    tags=["llm"],
    weight=5,
    expected_traits=["correct", "well-documented", "efficient"],
)

CODE_DEBUGGING = TestPrompt(
    id="code_debugging",
    label="Code Debugging",
    label_zh="代码调试",
    description="Identify and fix bugs in code",
    messages=[
        {
            "role": "user",
            "content": (
                "The following Python function has bugs. Identify all issues and "
                "provide a corrected version.\n\n"
                "```python\n"
                "def find_missing(nums):\n"
                "    n = len(nums)\n"
                "    expected_sum = n * (n + 1) / 2\n"
                "    actual_sum = 0\n"
                "    for i in range(n):\n"
                "        if nums[i] != None:\n"
                "            actual_sum += nums[i]\n"
                "    return expected_sum - actual_sum\n"
                "```"
            ),
        }
    ],
    tags=["llm"],
    weight=4,
    expected_traits=["thorough", "correct"],
)

# ── Scenario: Mathematical Reasoning ──────────────────────────

MATH_REASONING = TestPrompt(
    id="math_reasoning",
    label="Mathematical Reasoning",
    label_zh="数学推理",
    description="Solve a multi-step math problem with explanation",
    messages=[
        {
            "role": "user",
            "content": (
                "A train leaves Station A at 60 km/h. Another train leaves Station B "
                "at 80 km/h. The stations are 350 km apart. If they leave at the same "
                "time and travel toward each other, how long until they meet? "
                "Solve step by step."
            ),
        }
    ],
    tags=["llm"],
    weight=4,
    expected_traits=["step-by-step", "correct", "clear"],
)

LOGICAL_REASONING = TestPrompt(
    id="logical_reasoning",
    label="Logical Reasoning",
    label_zh="逻辑推理",
    description="Complex reasoning with constraints",
    messages=[
        {
            "role": "user",
            "content": (
                "There are five houses in a row, each painted a different color. "
                "The owner of each house drinks a different beverage, smokes a "
                "different brand of cigar, and keeps a different pet.\n"
                "1. The Brit lives in the red house.\n"
                "2. The Swede keeps dogs.\n"
                "3. The Dane drinks tea.\n"
                "4. The green house is immediately left of the white house.\n"
                "5. The green house's owner drinks coffee.\n"
                "6. The person who smokes Pall Mall rears birds.\n"
                "7. The owner of the yellow house smokes Dunhill.\n"
                "8. The man living in the centre house drinks milk.\n"
                "9. The Norwegian lives in the first house.\n"
                "10. The man who smokes Blends lives next to the one who keeps cats.\n"
                "11. The man who keeps horses lives next to the man who smokes Dunhill.\n"
                "12. The man who smokes Blue Master drinks beer.\n"
                "13. The German smokes Prince.\n"
                "14. The Norwegian lives next to the blue house.\n"
                "15. The man who smokes Blends has a neighbour who drinks water.\n\n"
                "Who owns the fish? Walk through your reasoning carefully."
            ),
        }
    ],
    tags=["llm"],
    weight=5,
    expected_traits=["logical", "step-by-step", "correct"],
)

# ── Scenario: Creative Writing ────────────────────────────────

CREATIVE_WRITING = TestPrompt(
    id="creative_writing",
    label="Creative Writing",
    label_zh="创意写作",
    description="Generate creative, stylistically rich text",
    messages=[
        {
            "role": "user",
            "content": (
                "Write a short story (200-300 words) about a robot that develops "
                "the ability to dream. The tone should be poetic and slightly melancholic."
            ),
        }
    ],
    tags=["llm"],
    weight=2,
    expected_traits=["creative", "coherent", "engaging"],
)

# ── Scenario: Summarization ───────────────────────────────────

SUMMARIZATION = TestPrompt(
    id="summarization",
    label="Text Summarization",
    label_zh="文本摘要",
    description="Condense a long text while preserving key information",
    messages=[
        {
            "role": "user",
            "content": (
                "Summarize the following in 3-4 sentences:\n\n"
                "Artificial intelligence (AI) has undergone remarkable transformation "
                "over the past decade. Deep learning, powered by large-scale neural "
                "networks and vast amounts of training data, has enabled breakthroughs "
                "in computer vision, natural language processing, and game-playing. "
                "More recently, the rise of large language models (LLMs) like GPT-4, "
                "Claude, and Gemini has demonstrated capabilities once thought to be "
                "decades away, including code generation, mathematical reasoning, and "
                "multimodal understanding. However, these advances also raise significant "
                "concerns about safety, alignment, bias, and environmental impact. "
                "Researchers and policymakers are actively working on frameworks to "
                "ensure AI development remains beneficial and aligned with human values."
            ),
        }
    ],
    tags=["llm"],
    weight=3,
    expected_traits=["concise", "accurate", "well-structured"],
)

# ── Scenario: Translation ─────────────────────────────────────

TRANSLATION = TestPrompt(
    id="translation",
    label="Translation (EN→ZH)",
    label_zh="翻译 (英→中)",
    description="Translate English to Chinese with accuracy and nuance",
    messages=[
        {
            "role": "user",
            "content": (
                "Translate the following to Chinese:\n\n"
                '"The limits of my language mean the limits of my world." '
                "-- Ludwig Wittgenstein"
            ),
        }
    ],
    tags=["llm"],
    weight=2,
    expected_traits=["accurate", "natural"],
)

# ── Scenario: Agentic / Tool Use ──────────────────────────────

AGENTIC_REASONING = TestPrompt(
    id="agentic_reasoning",
    label="Agentic Planning",
    label_zh="智能体规划",
    description="Plan and reason about multi-step tool use tasks",
    messages=[
        {
            "role": "user",
            "content": (
                "You are an AI assistant with access to the following tools:\n"
                "- search_web(query): search the internet\n"
                "- read_url(url): fetch and read a web page\n"
                "- write_file(path, content): write content to a file\n"
                "- send_email(to, subject, body): send an email\n\n"
                "Task: Research the latest quarterly earnings report for NVIDIA, "
                "summarise the key numbers, save the summary to a file, and email "
                "it to your team.\n"
                "Explain your step-by-step plan and what each tool call would do."
            ),
        }
    ],
    tags=["llm"],
    weight=4,
    expected_traits=["structured", "logical", "complete"],
)

# ── Scenario: Long Context ────────────────────────────────────

LONG_CONTEXT = TestPrompt(
    id="long_context",
    label="Long Context Understanding",
    label_zh="长上下文理解",
    description="Process and retrieve information from a long document",
    messages=[
        {
            "role": "user",
            "content": (
                "I will give you a long document. Read it carefully and then answer "
                "a question at the end.\n\n"
                + "The history of computing machinery can be traced back to ancient "
                "abacuses and mechanical calculators. " * 200
                + "\n\nBased on the document above, what is the main topic discussed?"
            ),
        }
    ],
    tags=["llm"],
    weight=3,
    expected_traits=["accurate", "relevant"],
)

# ── Scenario: Multimodal Understanding (text-only proxy) ──────

MULTIMODAL_UNDERSTANDING = TestPrompt(
    id="multimodal_understanding",
    label="Visual Description (Text Proxy)",
    label_zh="视觉描述 (文本代理)",
    description="Describe a scene in rich detail (tests spatial understanding)",
    messages=[
        {
            "role": "user",
            "content": (
                "Describe a detailed scene of a busy technology conference keynote. "
                "Include spatial layout, lighting, audience reactions, and speaker "
                "presentation style. Write as if you are seeing it."
            ),
        }
    ],
    tags=["multimodal", "llm"],
    weight=2,
    expected_traits=["vivid", "spatially-aware", "detailed"],
)

# ── Scenario: Instruction Following with Constraints ──────────

INSTRUCTION_FOLLOWING = TestPrompt(
    id="instruction_following",
    label="Constrained Instruction Following",
    label_zh="指令遵循",
    description="Follow precise formatting and content constraints",
    messages=[
        {
            "role": "user",
            "content": (
                "Write exactly 3 sentences about machine learning.\n"
                "Constraints:\n"
                "- The first sentence must start with 'Machine learning is'\n"
                "- The second sentence must contain the word 'however'\n"
                "- The third sentence must mention a specific application.\n"
                "- Do not use any bullet points or numbering.\n"
                "- Output ONLY the three sentences, nothing else."
            ),
        }
    ],
    tags=["llm"],
    weight=4,
    expected_traits=["precise", "constraint-compliant"],
)

# ── All prompts registry ──────────────────────────────────────

ALL_PROMPTS: list[TestPrompt] = [
    GENERAL_CHAT,
    CODE_GENERATION,
    CODE_DEBUGGING,
    MATH_REASONING,
    LOGICAL_REASONING,
    CREATIVE_WRITING,
    SUMMARIZATION,
    TRANSLATION,
    AGENTIC_REASONING,
    LONG_CONTEXT,
    MULTIMODAL_UNDERSTANDING,
    INSTRUCTION_FOLLOWING,
]

PROMPTS_BY_ID: dict[str, TestPrompt] = {p.id: p for p in ALL_PROMPTS}


def prompts_for_category(category: str) -> list[TestPrompt]:
    """Return prompts relevant to a model category."""
    return [p for p in ALL_PROMPTS if category in p.tags or "llm" in p.tags]
