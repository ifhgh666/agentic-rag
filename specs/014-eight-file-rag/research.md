# Research

- Decision：八个实际文件。Rationale：用户再次明确截图目标；26 文件不能满足。Alternatives：核心八文件外另放 helper、继续仅三组合并，均不满足本次目标。
- Decision：单向 graph→nodes→tools，状态/纯契约/提示为低层。Rationale：两个只读代理及 AST 核对已找到 memory/summary 与 retriever/query_planner 回边；normalize_query 下沉 tools，摘要上归 nodes。Alternatives：把摘要塞状态、治理塞 graph，会制造循环。
- Decision：保留原类/函数与 seam；纯模型/工具契约归 schemas。Rationale：原 Ollama/OpenAI/Fake adapter 是真实变化点，不能为少文件合成单实现。
- 直接合并估计约 5000 行，总复杂度不凭文件数下降；本次改善目录入口与相邻代码查阅。无未知依赖选型，不重复研究。
