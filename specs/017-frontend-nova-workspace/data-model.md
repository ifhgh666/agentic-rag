# 数据与前端状态

## E 联调记录
IntegrationRun：隔离路径、端口/PID、实际模型/编码器非敏感快照、资料与问题hash、启动/结束/退出码、服务请求状态与保护指纹。
IntegrationCase：id、原问题、预期事实（仅评分侧）、首次完整answer/sources、request/thread ID、公开SSE/实际usage、UI起止耗时、链路状态与事实评分分开。
每轮外部watchdog固定300秒；最多2个首答。状态含passed/failed/harness_aborted/not_run，未运行不算通过。凭据只在进程内，原始敏感提示词不进入报告。
测试文档由uploaded→processing→ready/failed，完成两题后只对该UUID执行确认删除；空清单、空检索和退出为收尾证据。

A健康/布局/登录保持原实现与A报告。

## B 当前会话
ChatSession: threadId:string|null、draft:string、action:ChatAction、pending:ClarificationEvent|null、pendingTurnId:string|null、turns:ChatTurn[]、runningTurnId:string|null、generation:number。仅内存，无persist。只有布局偏好沿用原localStorage。
ChatTurn: 本地id、requestId、threadId、原提交文字/动作、answer、sources、stages、analysis、retrieval、parentResults、executionEvents、usage、notice/error、status及当前简短状态。每轮独立。
状态：running→completed/partial/insufficient/clarification/cancelled/failed。必须收到complete；EOF无complete视为failed。部分正文和证据保留。失败恢复原文字，cancel不恢复空文字。
“最多2000字”；“running时禁止提交及新会话”；“会话/原文/密码不持久化”。同步提交锁由store的runningTurnId持有，不依赖React渲染延迟。
累计answer替换；retrieval快照覆盖；Parent按tool_call_id+parent_id去重。事件必须匹配generation、本地轮次以及一经绑定的requestId/threadId；未知事件/旧核验不展示。
pending仅由明确clarification pending=false或complete completed/partial/insufficient/cancelled清除；analysis成功及失败complete不能擅自清除。新会话清空本地投影，下次不发旧threadId。

## B 活动投影
保存原公开事件；显示列表按可靠tool_run_id（位于details）/tool_call_id/model_call_id关联更新。无ID保留独立行；不能按工具名合并并行调用。只展示公开事件和用量，不展示模型内部输出。实时/回放依据事件实际标志。

## 生命周期
切页不卸载控制器；退出及认证清除立即generation+1、abort、清空全部投影。signal传fetch；finally释放reader锁。前端abort不等于服务端模型已停止。

## C 文档
DocumentItem保持；单PDF及原生命周期。前端LogItem与日志页面退役；后台数据与API未改。

C页面本地状态：documents、名称查询、状态过滤(all/processing/ready/failed)、初始加载/刷新、上传或删除忙碌、列表错误/操作错误、待删除文档和确认错误、拖入高亮。均不持久化；列表始终为服务端DocumentItem投影。刷新请求序号防过期回写，processing才1800ms轮询，突变后强制刷新；卸载停止计时。上传回执暂存processing行，后续响应给出真实块数；删除失败不提前移除行。
