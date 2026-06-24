# approval · 审批域
> skill: lark-approval

## instances get
已知 instance_code，查询某审批实例的状态、表单内容与审批节点进度

### Avoid when
- 还没有 instance_code（先用 [[instances initiated]] 列出自己发起的实例）
- 要查的是审批任务而非实例（用 [[tasks query]]）

### Prerequisites
- 已有 instance_code（如来自 [[tasks query]] / [[instances initiated]]，或审批事件、发起结果等外部来源）

### Tips
- locale 控制返回文案语言（如 zh-CN / en-US）

### Examples

**按 instance_code 查询实例详情**
```bash
lark-cli approval instances get --instance-code "81D3****4E71"
```

**指定 locale 返回英文文案**
```bash
lark-cli approval instances get --instance-code "81D3****4E71" --locale "en-US"
```

## instances initiated
列出当前用户发起的审批实例，可按 definition_code 只看某类审批

### Avoid when
- 想查别人发起的实例（接口只返回当前用户自己的）
- 要查待办/已办的审批任务（用 [[tasks query]]）

### Tips
- definition_code 用于过滤到某一个审批定义（审批模板）

### Examples

**列出自己发起的实例（单页，默认分页大小）**
```bash
lark-cli approval instances initiated
```

**按审批定义（模板）过滤，只看某一类审批**
```bash
lark-cli approval instances initiated --definition-code "7C46****7A85"
```

## instances cancel
作为发起人撤回（撤销）一个仍在审批中的实例

### Avoid when
- 你是审批人想否决（用 [[tasks reject]]）
- 只是想退回到上一节点补材料（用 [[tasks rollback]]）

### Prerequisites
- 已有 instance_code（来自 [[instances initiated]] 或发起结果）
- 通常仅发起人可撤回，且实例仍在进行中

### Tips
- 已结束（通过/拒绝/已撤回）的实例无法再撤回

### Examples

**撤回一个进行中的实例**
```bash
lark-cli approval instances cancel --data '{"instance_code":"81D3****4E71"}'
```

## instances cc
把一个审批实例抄送给指定用户，让其知悉而不参与审批

### Avoid when
- 希望对方实际参与审批（用 [[tasks transfer]] 转交或 [[tasks add_sign]] 加签）
- 只是查看实例详情（用 [[instances get]]）

### Prerequisites
- 已有 instance_code（来自 [[instances initiated]] 或发起结果）

### Tips
- cc_user_ids 的 ID 类型需与 --user-id-type 一致（默认 open_id）

### Examples

**抄送给用户并附带说明**
```bash
lark-cli approval instances cc --data '{"instance_code":"81D3****4E71","cc_user_ids":["ou_3cda****83e1"],"comment":"请知悉"}'
```

**用 user_id 类型抄送给多人**
```bash
lark-cli approval instances cc --user-id-type "user_id" --data '{"instance_code":"81D3****4E71","cc_user_ids":["a1b2c3d4","e5f6g7h8"]}'
```

## tasks query
列出当前用户的审批任务（按 topic 区分待办 / 已办等），用于拿到 task_id 再去同意或拒绝

### Avoid when
- 要查的是审批实例而非任务（用 [[instances initiated]]）

### Tips
- topic 必填，用于选择任务分类（如待办/已办）

### Examples

**查询待办任务（topic 1）**
```bash
lark-cli approval tasks query --topic "1"
```

**查询已办任务（topic 2）**
```bash
lark-cli approval tasks query --topic "2"
```

**按审批定义过滤待办任务**
```bash
lark-cli approval tasks query --topic "1" --definition-code "7C46****7A85"
```

**查询未读知会（被抄送、待阅读的通知，非待审批任务，topic 17）**
```bash
lark-cli approval tasks query --topic "17"
```

## tasks approve
作为审批人同意（通过）一个待办审批任务

### Avoid when
- 要否决该任务（用 [[tasks reject]]）
- 想让别人来审（用 [[tasks transfer]] 转交 / [[tasks add_sign]] 加签）

### Prerequisites
- 已有 instance_code 与 task_id（来自 [[tasks query]]），且当前用户为该任务的审批人

### Tips
- 若审批节点要求填表单，用 form 字段提交

### Examples

**同意并附带意见**
```bash
lark-cli approval tasks approve --data '{"instance_code":"81D3****4E71","task_id":"123456789","comment":"同意"}'
```

**同意时提交节点要求的表单**
```bash
lark-cli approval tasks approve --data '{"instance_code":"81D3****4E71","task_id":"123456789","comment":"同意","form":"[{\"id\":\"user_name\",\"type\":\"input\",\"value\":\"张三\"}]"}'
```

## tasks reject
作为审批人拒绝（否决）一个待办审批任务，终止该流程

### Avoid when
- 想退回到前序节点补充材料而不终止流程（用 [[tasks rollback]]）
- 要同意（用 [[tasks approve]]）

### Prerequisites
- 已有 instance_code 与 task_id（来自 [[tasks query]]），且当前用户为该任务的审批人

### Tips
- 与 [[tasks rollback]] 区别：reject 终止流程，rollback 让流程退回重审

### Examples

**拒绝任务并附带理由**
```bash
lark-cli approval tasks reject --data '{"instance_code":"81D3****4E71","task_id":"123456789","comment":"预算不足，拒绝"}'
```

## tasks transfer
把一个待办审批任务整体转交给另一个人处理

### Avoid when
- 想在保留自己的同时增加审批人（用 [[tasks add_sign]] 加签）
- 自己直接处理（用 [[tasks approve]] / [[tasks reject]]）

### Prerequisites
- 已有 instance_code、task_id（来自 [[tasks query]]）与转交目标 transfer_user_id

### Tips
- transfer_user_id 的 ID 类型需与 --user-id-type 一致

### Examples

**把任务转交给指定用户**
```bash
lark-cli approval tasks transfer --data '{"instance_code":"81D3****4E71","task_id":"123456789","transfer_user_id":"ou_3cda****83e1","comment":"转交给你处理"}'
```

**用 user_id 类型指定转交目标**
```bash
lark-cli approval tasks transfer --user-id-type "user_id" --data '{"instance_code":"81D3****4E71","task_id":"123456789","transfer_user_id":"a1b2c3d4"}'
```

## tasks add_sign
在当前审批节点增加审批人（加签），由 add_sign_type 决定前加签/后加签/并加签

### Avoid when
- 想把任务整体交给别人而非增加（用 [[tasks transfer]]）

### Prerequisites
- 已有 instance_code、task_id（来自 [[tasks query]]）、加签人 add_sign_user_ids 与 add_sign_type

### Tips
- add_sign_type 控制加签方式（前/后/并），按业务语义选择

### Examples

**前加签：先让指定人审批（add_sign_type 1）**
```bash
lark-cli approval tasks add_sign --data '{"instance_code":"2893****BCAE","task_id":"6955****7956","add_sign_user_ids":["ou_3cda****83e1"],"add_sign_type":1,"comment":"前加签"}'
```

**后加签：自己审批后再让指定人审批（add_sign_type 2）**
```bash
lark-cli approval tasks add_sign --data '{"instance_code":"2893****BCAE","task_id":"6955****7956","add_sign_user_ids":["ou_3cda****83e1"],"add_sign_type":2,"comment":"后加签"}'
```

**并加签：与多名加签人会签（add_sign_type 3，会签 approval_method 1）**
```bash
lark-cli approval tasks add_sign --data '{"instance_code":"2893****BCAE","task_id":"6955****7956","add_sign_user_ids":["ou_3cda****83e1","ou_8a1f****e6f7"],"add_sign_type":3,"approval_method":1,"comment":"并加签"}'
```

## tasks rollback
把审批退回到之前的某个/某些节点重新审批（流程继续，不终止）

### Avoid when
- 想直接否决并终止流程（用 [[tasks reject]]）
- 想撤销整个实例（用 [[instances cancel]]）

### Prerequisites
- 已有 instance_code、task_id（来自 [[tasks query]]）与要退回到的 node_ids

### Tips
- node_ids 指定退回到哪些节点；与 reject 不同，流程不会被终止

### Examples

**退回到指定节点重新审批**
```bash
lark-cli approval tasks rollback --data '{"instance_code":"2893****BCAE","task_id":"6955****8956","node_ids":["manager_node_id"],"comment":"请补充材料后重新提交"}'
```

## tasks remind
催办（提醒）某审批任务的待办审批人尽快处理

### Avoid when
- 自己就是审批人要直接处理（用 [[tasks approve]] / [[tasks reject]]）

### Prerequisites
- 已有 instance_code 与 task_ids（来自 [[tasks query]]）

### Tips
- task_ids 是数组，可一次催办同一实例下的多个任务

### Examples

**催办单个待办任务**
```bash
lark-cli approval tasks remind --data '{"instance_code":"81D3****4E71","task_ids":["6955****7956"],"comment":"麻烦尽快处理"}'
```

**一次催办同一实例下的多个任务**
```bash
lark-cli approval tasks remind --data '{"instance_code":"81D3****4E71","task_ids":["6955****7956","6955****8956"]}'
```
