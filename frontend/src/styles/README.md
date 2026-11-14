# 前端样式

`app.css` 是 Tailwind v4 入口，`tokens.css` 定义浅色 Nova 中性色、字体、圆角和状态变量。新组件来自 `components/ui/` 的官方 base-nova 本地源码，图标使用 Lucide，进退场由 Motion 管理。

Geist 字体随项目自托管，许可证位于 `assets/fonts/OFL.txt`；页面不再请求 Google Fonts。B 的问答使用 `chat.css`，输入固定在工作区底部，消息区独立滚动，过程及原文使用原生 details。C 的知识库使用 `knowledge.css`，包含单文件拖放、名称/状态交集、局部滚动表格和删除确认。知识库表格建立定位容器，使隐藏的辅助文本也受局部滚动区域约束。

D 确认三页均无旧作用域消费者后，移除 `legacy.css`、入口导入及 tokens 中两条旧兼容规则。原文件与清理前后截图/样式对照保存在 `output/frontend017/phase-d-20261102-01/`。当前样式由 Nova tokens、chat 和 knowledge 三部分提供；保留各页面已确认的视觉与交互。
