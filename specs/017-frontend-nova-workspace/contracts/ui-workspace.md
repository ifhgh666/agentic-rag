# 界面与兼容契约（B修订）

原四图只为历史参考：登录保持上移后单列效果，问答采用同一Nova视觉，原侧栏和日志图已被用户取代。

## 全局
保留A的浅色neutral、Geist本地资源、Lucide、Motion及reduced-motion，按钮约44px高、可见焦点。导航只有/chat与/knowledge；/logs替换/chat，不新增历史记录。Knowledge保持legacy作用域；Chat使用独立Nova样式。

## B输入与阅读
Enter发送，Shift+Enter换行；组合输入/isComposing/229/repeat不发送；form和键盘共用同步提交锁。只接收非空<=2000字。运行中输入和新会话禁用。非cancel立即追加用户消息并清空draft，失败恢复原文字且不重试。
消息区独立滚动、底部输入；只有用户位于底部附近时自动跟随。每轮助手正文/来源/折叠过程归属于同一轮。所有过程默认折叠；运行中状态由公开事件更新，不模拟进度。
来源在答案下，Child/Parent完整文本以纯文本details展开；页码真实。Markdown基础GFM，skipHtml、不接rehype-raw，图片文字占位、安全链接；表格代码局部横向滚动，复制原始Markdown并反馈结果。

## B接口
保留POST /api/chat/stream的question/thread_id/action及所有SSE wire字段，前端函数新增可选第五参数signal。无终态EOF为失败；reader释放。旧verification/evaluation不生成UI。
pending/四动作以服务端为准；切页保留读取/状态；退出清除并拒绝迟到事件。后台日志/API和模型/配置/正式数据不变。

## C/D
C单独完成知识库表格/过滤/拖入/确认；D三页最终矩阵。本轮不执行。

## C当前契约
当前仅实施C，前述“本轮不执行”为B历史。知识库按原图浅色表格、单PDF拖入/选择；名称与状态交集过滤，不改变API排序。processing/ready/failed、父/子数量与失败原因依据真实接口，处理中不虚构进度/块数；处理完成后可检索的说明不作为实际ready标记。
删除通过本地Nova AlertDialog确认，默认聚焦取消；取消/Escape不调用删除，进行中防重入及关闭，失败保留弹框/文档并反馈，成功后刷新并将焦点放回可用控件。选择/拖入多文件整批拒绝，非PDF拒绝，同文件可重选。无匹配和空库分别展示；刷新失败保留最后成功列表并允许重试。表格小屏局部滚动，按钮/筛选可见且可键盘操作。
原GET/POST/DELETE /api/knowledge/documents和DocumentItem、1800ms processing轮询保持；不改SSE、会话状态或后端。
