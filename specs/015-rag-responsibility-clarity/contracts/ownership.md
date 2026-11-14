# Ownership and Compatibility Contract

模块归属改变，类/函数合法参数、返回、算法和实例共享关系保持；仓库内调用与采集指纹迁移，仓库外调用按归属表更新路径。不留成套转发文件或动态 sys.modules 别名。

core 各模块只有一份实现；rag 仍实际持有模型循环、节点、工具准入与路由，不能成为一组转发壳。provider、模型共同调用、索引、会话、答案与交付分别有明确 interface。core.__init__ 不导入整套系统。

P1/P2、两模型协议、共享计数/租约、原绝对期限、缓存、原文和引用、历史及诊断行为保持。旧 EvidenceSelector/QueryGenerator 等独立能力只隔离，不删除或重新接回主图。采集旧冻结批次不修改，不因换路径放宽 continuation_code_mismatch。

014 的“所有实现只八文件”不再作为新方案验收目标；新的八文件范围只限 Agent 核心。必须在本方案验收后才修改现有精确八文件守护和实施。
