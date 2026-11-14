# 017 A 登录区上移调整 — 2026-10-29

授权：用户提供运行页面截图，要求登录内容整体上移。本轮仅调整 A 登录页排版，未进入 B/C/D。

## 改动

- `frontend/src/pages/Login.tsx`：登录内容仍水平居中，上下剩余空间改为 1:3 分配；标识、标题、表单、管理员提示同步上移。保留上下各 80px 的最小空间，短屏自然滚动，无负位移裁切。
- `spec.md`：记录用户新确认的中上部布局；原垂直居中效果图和 A 报告保留为历史证据。
- 本次未增加依赖，未改认证、后端配置或知识库数据；T001–T015 状态不变，T016–T029 未执行。

## 实际验证

命令工作目录均为 `frontend`：

- `npm run build`：退出 0，TypeScript 与 Vite 构建通过。原始记录：`frontend/output/frontend017/login-position-20261029/build.log`。
- `npm test -- src/pages/Login.test.tsx`：退出 0，既有登录测试全部通过。原始记录：`frontend/output/frontend017/login-position-20261029/login-tests.log`。测试使用受控接口，不代表真实登录或模型验证。
- 通过开发服务器加载独立 `login-preview.html`，直接渲染产品 Login 和 MotionProvider。1280×720：登录区顶部约 104px，比原垂直居中位置上移约 24px，宽约 384px，保持水平居中。屏幕越高，可分配留白越大，上移距离随之增加。
- 390×520：文档高约 624px，内容顶部约 80px，表单底部约 544px，页脚顶部约 576px；允许纵向滚动，没有水平溢出或页脚重叠。临时视口已恢复，预览标签已关闭。
- 截图：`frontend/output/frontend017/login-position-20261029/login-desktop.jpg`、`login-short.jpg`。独立预览未提交真实登录、未触发模型或检索调用。

浏览器 Playwright 连接不可用、完整页截图 API 失败后，改用 CUA 视口截图成功；这属于验证工具限制，未发现当前布局失败。没有覆盖既有历史失败。

后续范围仍为 B 问答工作区与 C 知识库/日志页面，需另行明确授权。本次局部调整完成，待用户查看。

**报告后暂停，等待用户验收**。
