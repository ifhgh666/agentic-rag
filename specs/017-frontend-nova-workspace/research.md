# 研究与决策：Nova 前端知识工作台

## E 真实联调（2026-11-02）
Decision：复用当前真实模型及产品工厂；隔离数据/账号/缓存，正常ONNX/BM25工厂加载。保留默认词表/词干化，使用FASTEMBED_CACHE_PATH和离线缓存。
Rationale：app.main导入立即创建默认应用，必须先环境隔离；正常参考工厂不读取旧超时/总模型额度，采集watchdog必须单列。只读代理e_integration_research已核对产品源码及本机FastEmbed实际加载代码，主代理再实际预检。
Alternatives：真实账号密码不可从hash还原；不修改正式账号。仅图层采集无法覆盖HTTP/上传/前端；受控API不满足用户选择。SPARSE_OFFLINE_FALLBACK=true会改变编码，HF_HUB_CACHE单独不足，不采用；不需要旧D的Sparse路径注入。
来源：backend/app/main.py、config.py、core/reference_model.py、rag/graph_state.py；D:/newsoft/Lib/site-packages/fastembed/common/utils.py与model_management.py；output/reference016/phase-d/resources/bm25/english.txt，SHA256=019f104ba2ed07436d05f9cdd3383034ad66014edc27fc651f837e1a038b6451。原A–D研究内容保持。

## C（2026-10-29）
Decision：复用既有Nova/Button/Input和已安装BaseUI，新增官方base-nova AlertDialog本地适配；原生状态select，REST不变。Rationale：知识库删除需要明确焦点/键盘确认，原window.confirm不与页面风格一致；同一基础库已有AlertDialog，不需依赖升级。原registry已保存于output/frontend017/phase-c-20261029-01/upstream，SHA256为97454324…c57a8af；本机类型确认Popup初始/最终焦点及Root可取消关闭事件。Alternatives：第二套Dialog基础库、整套上传组件和查询缓存扩大范围，不采用。使用真实服务端状态、无虚构进度；无新的依赖选择或研究代理任务。

## B 修订（本次权威决定）
2026-10-29 用户明确批准移除前端日志与右侧面板，改为连续对话和对话内折叠。下文 A 决策为历史；B 按本节覆盖原未来设想。

**Decision**: 精确固定 Zustand 5.0.16、react-markdown 10.1.0、remark-gfm 4.0.1，均MIT，React18兼容。使用zustand/vanilla createStore和zustand useStore，不用traditional/immer/persist或第二套状态库。Markdown skipHtml、图片转文字、安全链接；无rehype-raw/高亮/数学依赖。原生details无需新折叠库，不安装resizable/dnd/Gradio。
**Rationale**: speckit-plan指定的只读研究代理b_dependency_research已查官方npm已发布元数据；Zustand无必需runtime依赖，React peer>=18，Markdown解析依赖属于必要AST链，需审计实际dedupe。用当前会话内存投影支持切页不断流，退出清除和事件代次校验避免污染。
**Alternatives**: Redux/查询缓存/永久会话、独立调试页、右侧可调面板会扩大本次范围；前端复制原项目Gradio栈会破坏统一组件语言。选择只借鉴原项目按轮折叠查询/工具和流式最终答案。
**Sources**: [Zustand元数据](https://registry.npmjs.org/zustand/5.0.16)、[createStore](https://zustand.docs.pmnd.rs/apis/create-store)、[useStore](https://zustand.docs.pmnd.rs/hooks/use-store)、[Markdown](https://github.com/remarkjs/react-markdown#security)、[GFM](https://github.com/remarkjs/remark-gfm)、[原项目界面](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/ui/gradio_app.py)、[原项目过程](https://github.com/GiovanniPasq/agentic-rag-for-dummies/blob/main/project/core/chat_interface.py)。无未解决技术澄清。

日期：2026-10-29。speckit-plan Phase0 由 nova_dependency_research 子代理只读核对官方源码及实际 npm 元数据，主代理核对本地代码。没有未解决的技术澄清。

## 组件与构建
**Decision**: 使用已发布 base-nova registry 的最小组件源码。官方响应已展开 Nova Tailwind 类，可直接入仓库，无需安装 shadcn 运行包、tw-animate-css 或复制整份作者模板样式。Base UI 负责可访问交互，组件代码由项目控制。
**Rationale**: 当前没有第二套基础组件。React18 与 BaseUI1.9.0/Motion14.7.1兼容；Tailwind4.3.3 的 Vite 插件支持 Vite6，无需升级现有框架。
**Alternatives**: Radix 与 Base UI 二选一，选官方 Base 路径；不混用。整站 dashboard 模板、React19/Vite 升级均无必要。不把 GitHub master 当已发布产物。

## 实际版本与依赖最小化
BaseUI1.9.0、cva0.7.1、cn0.5.0、Lucide1.64.0、Motion14.7.1；Tailwind/Vite插件4.3.3。cn要求Node>=22，本机22.23.2满足。仅直接使用 cn，不再直接引入 clsx/tailwind-merge；cva 的 clsx2.1.1和 Motion 的 framer-motion14.7.1 属必要传递依赖。BaseUI 的 date-fns 可选peer不安装。后续 B 库有使用点再安装。

## 状态与兼容
**Decision**: A 局部导航与健康 hook 使用 React 状态；B 会话/跨页面状态统一 Zustand。当前会话是后端事实的前端投影，不另建永久聊天数据库。既有 token 存储策略保持。
**Rationale**: 当前 state 全在页面；先安装 Zustand 却不用会违反用户的依赖约束。保留 hash 路由，避免第二次框架迁移。
**Alternatives**: Redux、查询缓存库、永久会话列表和同步存储原文不在范围。

## 分阶段 CSS
**Decision**: 新基础样式与局部 legacy-content 兼容作用域分离；A 不迁移问答/文档/日志业务。
**Rationale**: 原 app.css 是深色基础与浅色追加覆盖，全局 label/input/headings 会污染新组件。作用域隔离后可逐页迁移，避免 A 越过 B/C。
**Alternatives**: 全局强制覆盖会让旧页面或新基础组件不可预测；一口气改完四页越过阶段授权。

## 官方来源
- [Nova Button](https://ui.shadcn.com/r/styles/base-nova/button.json)、[Input](https://ui.shadcn.com/r/styles/base-nova/input.json)、[Sheet](https://ui.shadcn.com/r/styles/base-nova/sheet.json)
- [shadcn registry](https://github.com/shadcn-ui/ui/tree/main/apps/v4/registry)、[MIT](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md)
- [Base UI](https://github.com/mui/base-ui/blob/master/packages/react/package.json)、[cn](https://github.com/shadcn-ui/cn)
- [Motion](https://motion.dev/docs/react-installation)、[Lucide](https://lucide.dev/guide/react)、[Tailwind Vite](https://tailwindcss.com/docs/installation/using-vite)
- [Geist 字体](https://github.com/vercel/geist-font)

包元数据使用 npm view 的实际已发布响应；原 npm 默认缓存路径不可写，后续显式指定 output 内缓存，不修改全局 npm 配置。下载来源、许可证和 SHA-256 随阶段证据保存。
