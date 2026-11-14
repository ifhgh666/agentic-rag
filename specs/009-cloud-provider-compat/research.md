# Phase 0 Research: 云兼容端点的结构化输出兼容

本文件记录关键技术决策、依据与被否决的替代方案。所有“实测”均指 2026-10-15 在本机（Python 3.12.4、`openai 3.19.2`、`httpx2 2.13.0`、`brotli 1.0.9`）真实执行的结果。

## D1. 如何消除“云端调用整体不可用”

**Decision**: 在云端提供商构造 HTTP 客户端时显式不使用压缩编码（`Accept-Encoding: identity`），不改动用户环境、不新增依赖。

**Rationale**:
- 实测复现：`brotli.Decompressor.process(payload, output_buffer_limit=1024)` → `TypeError: takes no keyword arguments`；不带该参数调用成功。`httpx2._decoders.BrotliDecoder.decode` 固定传该参数，因此任何 brotli 压缩返回都会抛错。
- 实测：同一 DeepSeek 端点，加 `Accept-Encoding: identity` 后普通对话调用成功；不加则复现失败。
- 该缺陷位于第三方 C 绑定与 HTTP 客户端的版本组合，属于环境问题；产品侧规避比要求用户改环境更可靠，也符合“不把环境准备与功能可用性混为一谈”。

**Alternatives considered**:
- *卸载或升级 `brotli`*：能修好环境，但需要用户同意改动本机 Python 环境，且升级后仍需回归；作为**可选**后续项保留，不作为本功能前提。
- *在 `httpx2` 层打补丁*：需要触碰第三方包或私有 API，脆弱且不可交付。
- *要求用户改用不支持压缩的端点*：把产品缺陷转嫁给用户配置。

## D2. 结构化输出回退策略

**Decision**: 保留严格 JSON Schema 模式为首选；仅当端点以“该 response_format 类型不可用”类错误拒绝时，把 schema 文本注入提示词并改用通用 JSON 模式重试**一次**。返回内容仍由同一个 schema 校验。

**Rationale**:
- 实测：同一端点 `response_format={"type":"json_schema",...}` → 400 `This response_format type is unavailable now`；`{"type":"json_object"}` → 返回合法 JSON。
- 入口分析的 schema **未**进入提示词（`query_analysis.py` 的 `schema_text` 只用于缓存键与 token 估算），因此单纯去掉 `response_format` 会让模型无从得知字段；必须同时注入 schema 文本，回退才有意义。
- 校验仍在 `complete_model` 用同一 `response_schema` 执行（`model_validate_json`），因此回退不降低校验强度，只改变约束机制。

**Alternatives considered**:
- *始终用通用 JSON 模式*：会削弱支持严格模式的端点的约束力，属于能力倒退。
- *让用户换成支持严格模式的端点*：可行但把兼容性责任推给用户。
- *在测试外壳里绕过*：已评估并否决——那将得到“补丁的产物”而非被测系统的行为，验收会失真。

## D3. 重试次数与失败分类

**Decision**: 同一逻辑调用最多 2 次实际请求（1 次严格 + 1 次回退）。两次都以“模式不可用”告终时归为提供商不可用；模型返回内容不合法仍走既有“输出非法”路径。

**Rationale**:
- 无界重试会突破请求级调用预算与 300 秒期限（FR-008）。
- 当前入口分析把一切非超时异常归为 `model_unavailable`，这已经满足“不得记为输出非法”（FR-005）；风险在于回退实现在失败时把能力问题误报成输出问题，故需在契约中固定。
- 现有无依据把端点能力不足升级为新的对外错误码，新增顶层错误码会牵动前端类型与契约测试，超出本功能必要性。

**Alternatives considered**: *指数退避重试*（对本场景无意义，端点能力不会自愈）；*新增对外错误码 `structured_output_unsupported`*（留作后续需要时的增量）。

## D4. 可观测字段的落点

**Decision**: 在 `ModelResult` 上增加“实际结构化模式”和“是否回退”两个字段，随既有模型轨迹写入，并进入执行事件的 `details`。不新增对外顶层 SSE 字段。

**Rationale**:
- FR-004 要求可观测，而 `details` 已是被前端过程面板消费的自由字段集合，追加键不破坏既有契约。
- 顶层事件字段属于公共契约，新增会牵动 `frontend/src/types/api.ts` 与契约测试；本功能目标是可用性与可诊断性，不值得扩大契约面。

**Alternatives considered**: *新增顶层 `structured_mode` 事件字段*（契约面扩大，收益不足）；*只写本地 loop_traces*（对运维不可见，不满足“请求记录”语义）。

## D5. 推理模型与空正文

**Decision**: 保持既有“空正文即无有效输出”的判定不变，不把 `reasoning_content` 当答案，也不因推理模型而修改预算数值。

**Rationale**:
- 实测所选模型会在 `content` 为空时返回 `reasoning_content`；若把推理内容并入答案，会违反“不输出私有推理”的既有约束。
- 现有 `visible_content` 已剥离 `<think>` 段；本功能只需确保回退路径不绕过该处理。

**Alternatives considered**: *自动提高输出 token 上限以容纳推理*（属于预算调整，需单独授权，不在本功能范围）。

## D6. 不引入依赖变更

**Decision**: 本功能不修改 `backend/requirements.txt`，不安装或卸载任何包。

**Rationale**: 两处修复都在产品代码内完成；把环境修复作为可选项写进报告，交由用户决定。

**Alternatives considered**: *把 `brotli` 版本固定写入依赖清单*（依赖清单当前并未声明 `brotli`，它只是 `httpx` 生态的可选加速件，固定它意义有限）。
