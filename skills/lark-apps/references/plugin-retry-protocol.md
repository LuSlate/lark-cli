# 插件实例校验失败重试协议

`+plugin-instance-create` 或 `+plugin-instance-update` 返回 `ok: false` 且 error.type 为 `validation` 时，按本协议处理。

## 触发条件

CLI 返回格式：
```json
{
  "ok": false,
  "error": {
    "type": "validation",
    "subtype": "invalid_argument",
    "message": "formValue validation failed:\n- ...\n- ...",
    "hint": "fix the issues above and retry"
  }
}
```

## 重试流程

```
校验失败
  ↓
Step 1: 解析 error.message 中的每条违规（以 "- " 开头的行）
  ↓
Step 2: 逐条修正 formValue / paramsSchema
  ↓
Step 3: 重新调用 +plugin-instance-create（加 --force）或 +plugin-instance-update
  ↓
校验通过？
  ├── 是 → 继续后续流程
  └── 否 → 回到 Step 1（累计 ≤ 3 次）
         └── 3 次仍失败 → 上报用户，附带最后一次的完整错误信息
```

## 常见违规及修正方式

| 违规信息 | 原因 | 修正 |
|---------|------|------|
| `forbidden Handlebars syntax at formValue.xxx: {{#if` | formValue 中使用了控制语法 | 改为纯 `{{input.xxx}}` 或自然语言描述 |
| `paramsSchema property "x" type "number" is invalid` | 参数类型不在 string/array 范围 | 改为 `"type": "string"` 或 `"type": "array"` |
| `paramsSchema property "x" is array but missing items` | array 类型缺少 items 定义 | 补上 `"items": {"type": "string"}` |
| `paramsSchema property "x" missing description` | 参数缺少描述 | 补上 `"description": "..."` |
| `{{input.xxx}} at formValue.yyy is not defined in paramsSchema` | formValue 引用了未定义的变量 | 在 paramsSchema.properties 中补充定义，或修正拼写 |
| `paramsSchema property "x" is never referenced` | 定义了变量但 formValue 中没有引用 | 在 formValue 中补充 `{{input.x}}`，或从 paramsSchema 移除 |

## 修正要点

1. **不要直接编辑 capability JSON 文件** — 必须通过 CLI 命令重新提交
2. **Create 重试用 `--force`** — 覆盖上一次失败写入的文件
3. **Update 直接重新调用** — 会覆盖现有配置
4. **保持 paramsSchema 和 formValue 的一致性** — 修一个通常要同步改另一个
5. **3 次失败后不要继续猜** — 上报用户并附带完整错误，让用户决策
