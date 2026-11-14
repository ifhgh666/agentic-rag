# 聊天流

`POST /api/chat/stream` 沿用现有请求体和事件字段。模型分流和直接回答可产生实际 `node`、`model_start`、`model_call` 和用量记录。直接回答复用累计 `answer`、空 `sources` 和 `complete.status=completed`。仅进入文档改写时发布 `analysis`。需要补充时发布现有 `clarification`；分流失败时复用现有错误终态。
