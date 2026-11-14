# Implementation Plan: 第一组证据能力合并

**Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)
**Branch**: 实际检出 codex/model-driven-agent-loop，未创建/切换；setup-plan 的 BRANCH=013-evidence-consolidation 为目录回退值。

**Status**: 阶段 A 工程完成，见 [报告](phase-a-report.md)；7 项任务完成不等于用户验收。

## Summary

将 procedure_evidence.py 四常量与五函数原样搬入 evidence.py，补 Path 导入，移除相对导入及旧文件，迁移一个测试导入。保留 normalized、_matching_section、recover_paragraphs、read_saved_markdown、eligible_units。正常图不恢复 EvidenceSelector.select。不另开研究代理：前序调查已完成，当前没有未知技术选型。

## Technical Context

**Language/Version**: 既有 Python 3.11+。
**Primary Dependencies**: re、pathlib 及已有依赖，无新增依赖。
**Storage**: 无新存储，不操作正式数据和 .env。
**Testing**: pytest；既有证据/图职责/独立兼容检查，补安全读取和单元筛选边界。
**Target Platform**: 当前 Windows。
**Project Type**: 既有 Web 后端内部整理。
**Performance Goals**: rag 源文件 29→28，不承诺时延/内存提升。
**Constraints**: 搬移函数/常量与 evidence 旧定义 AST 等价；旧路径移除已接受；不重命名函数局部 normalized。
**Scale/Scope**: evidence.py 合并、procedure_evidence.py 删除、一份测试迁移和补边界；规划/报告与临时证据另记。

## Constitution Check

前后均通过，无例外：仅阶段 A；证据职责相邻收拢，不吸收治理/检索/传输；保留原文/来源与安全；不操作正式数据；工程与真实质量结论区分。

## Project Structure

```text
specs/013-evidence-consolidation/
  spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
  checklists/requirements.md, contracts/compatibility.md, phase-a-report.md
backend/app/rag/evidence.py
backend/tests/unit/test_v3_7_procedure_evidence.py
output/merge013/phase-a/  # 基线/保护/日志/差异，已 ignore
```

**Structure Decision**: 不新增生产模块、兼容转发或抽象层。

## 阶段、验证与停止点

仅一个交付阶段 A，对应 tasks 全部；Setup/Foundation/US1/Polish 是阶段内任务分组，不另分验收阶段。

保存源码/git基线 → 准备保护 → 合并前定向检查 → 原样搬移/迁移 → 补直接安全边界检查 → 同集合及间接调用回归 → AST/引用/范围审计 → phase-a-report 后暂停。

保护复用 012 最终 guard，输出改到本阶段；禁网络、真实 Dense、正式数据，禁用 dotenv。先 procedure/evidence/架构与 P3 兼容，再 graph/pipeline/grounding/query_planner。无新增风险不跑全量/前端。失败日志不覆盖，修复补测用独立标签。

FR-001/003：AST、原始单元/选择/来源及图回归；FR-002：旧文件删除与引用扫描；FR-004/006：源码 manifest/报告；FR-005：guard/日志。AST 对比全部五函数四常量和 evidence 原有定义。

## Complexity Tracking

无新抽象和宪章例外。已批准旧路径失效，迁移见契约。不将既有失败修复或其他组作为自动后续。
