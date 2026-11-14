# E入口采集CLI：继续模式

`--stop-on-failure` 与 `--continue-on-failure` 必须且只能指定一个。旧停止模式不变。继续模式记录单题模型/格式/质量失败及uncertain后继续下一题，不重试，不放宽预算或模型配置，不覆盖输出目录。人工中断与越预算仍终止。

继续模式配合 `--resume-from` 可沿用已审阅failed/uncertain的首次结果，仅调用未运行后缀。来源fixture/config/model/生产代码、原首答及审阅记录仍需一致；被引用失败保持failed，不需要伪造passed addendum。

完成且全通过为 `completed` / exit 0；覆盖完但有failed/uncertain为 `completed_with_failures` / exit 1；批次中断为 `stopped` / exit 1，准备错误exit 2。新summary增加uncertain计数及单题failure_reason，manifest记录实际继续协议。仅本地采集产物，无产品API变更。
