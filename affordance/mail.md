# mail · mail 域
> skill: lark-mail

## multi_entity search
写信时按关键词搜索联系人（人/邮箱地址），用于补全收件人

### Avoid when
- 要搜索邮件内容（用 [[user_mailboxes search]]）
- 要管理已存的个人邮箱联系人记录（用 [[user_mailbox.mail_contacts list]] 等）

### Tips
- size 控制返回条数，默认 20，范围 1-20

### Examples

**按关键词搜索联系人**
```bash
lark-cli mail multi_entity search --data '{"query":"周会"}'
```

**限制返回条数**
```bash
lark-cli mail multi_entity search --data '{"query":"周会","size":5}'
```

## user_mailbox.drafts cancel_scheduled_send
取消一封已设定时发送但尚未发出的邮件

### Avoid when
- 邮件已经发出去了想撤回（用 [[user_mailbox.sent_messages recall]]）

### Prerequisites
- message_id 为已设置定时发送的邮件 id（来自 [[user_mailbox.drafts send]] 的结果）

### Examples

**取消定时发送**
```bash
lark-cli mail user_mailbox.drafts cancel_scheduled_send --message-id "268d****50fd" --user-mailbox-id "me"
```

## user_mailbox.drafts create
创建一封邮件草稿（不立即发送），且你已有现成的 RFC 5822(EML) 原文

### Avoid when
- 想直接撰写新邮件而不手工拼 base64 MIME（起草用 [[+draft-create]]，撰写并发送用 [[+send]]，回复用 [[+reply]] —— 这些高层命令默认存草稿，加 --confirm-send 才真正发送）
- 要修改已有草稿（用 [[user_mailbox.drafts update]]）
- 要把草稿发出去（先 create/update 再用 [[user_mailbox.drafts send]]）

### Tips
- raw 为 base64url 编码的完整 RFC 5822(EML) 邮件内容，含所有邮件头(Subject/From/To/Cc/Bcc)与正文

### Examples

**用 base64url 编码的 EML 创建草稿**
```bash
lark-cli mail user_mailbox.drafts create --user-mailbox-id "me" --data '{"raw":"Q29udGVudC1UeXBlOiB0ZXh0L3BsYWluOyBjaGFyc2V0PSJ1cy1hc2NpaSIKTUlNRS1WZXJzaW9uOiAxLjAKQ29udGVudC1UcmFuc2Zlci1FbmNvZGluZzogN2JpdAp0bzogInRvIiA8dG9AeHh4Lnh4Pgpmcm9tOiAiZnJvbSIgPGZyb21AeHh4Lnh4PgpzdWJqZWN0OiB0aGlzIGlzIGEgc3ViamVjdAoKdGhpcyBpcyB0aGUgbWVzc2FnZSBib2R5Lg"}'
```

## user_mailbox.drafts delete
删除一封草稿

### Prerequisites
- draft_id 来自 [[user_mailbox.drafts list]]

### Examples

**删除草稿**
```bash
lark-cli mail user_mailbox.drafts delete --draft-id "268d****50fd" --user-mailbox-id "me"
```

## user_mailbox.drafts get
已知 draft_id，获取草稿内容

### Avoid when
- 读草稿是为了接着改它 —— 用 [[+draft-edit]]（读改写一体、MIME-safe）；纯查看内容用本命令即可

### Prerequisites
- draft_id 来自 [[user_mailbox.drafts list]] 或 [[user_mailbox.drafts create]]

### Tips
- format 取值 metadata / full（默认）/ raw

### Examples

**获取草稿内容**
```bash
lark-cli mail user_mailbox.drafts get --draft-id "268d****50fd" --user-mailbox-id "me"
```

**以原始格式获取草稿（format 与 CLI 输出 --format 同名，走 --params）**
```bash
lark-cli mail user_mailbox.drafts get --draft-id "268d****50fd" --params '{"format":"raw"}' --user-mailbox-id "me"
```

## user_mailbox.drafts list
列出草稿，拿到 draft_id 供查看/更新/发送/删除使用

### Examples

**列出草稿**
```bash
lark-cli mail user_mailbox.drafts list --user-mailbox-id "me"
```

## user_mailbox.drafts send
发送一封已建好的草稿；传 send_time 可定时发送

### Avoid when
- 要一次发送多封草稿 —— 用 [[+draft-send]]（逐封发送、隔离单封失败、聚合结果）
- 要取消已设的定时发送（用 [[user_mailbox.drafts cancel_scheduled_send]]）
- 邮件已发出想撤回（用 [[user_mailbox.sent_messages recall]]）

### Prerequisites
- draft_id 来自 [[user_mailbox.drafts create]] / [[user_mailbox.drafts list]]

### Tips
- send_time 为 Unix 秒级时间戳，需至少为当前时间+5 分钟；不传则立即发送

### Examples

**立即发送草稿**
```bash
lark-cli mail user_mailbox.drafts send --draft-id "268d****50fd" --user-mailbox-id "me"
```

**定时发送草稿**
```bash
lark-cli mail user_mailbox.drafts send --draft-id "268d****50fd" --user-mailbox-id "me" --data '{"send_time":1720000000}'
```

## user_mailbox.drafts update
全量替换已有草稿的内容

### Avoid when
- 想增量改草稿而不重拼整封 EML —— 用 [[+draft-edit]]，它做 MIME-safe 读改写、尽量保留未改的结构/附件/邮件头；裸 update 是全量替换，需自备完整 base64 EML
- 要新建草稿（用 [[user_mailbox.drafts create]]）

### Prerequisites
- draft_id 来自 [[user_mailbox.drafts list]] 或 [[user_mailbox.drafts create]]

### Tips
- raw 为 base64url 编码的完整 RFC 5822(EML) 邮件内容，全量替换

### Examples

**全量替换草稿内容**
```bash
lark-cli mail user_mailbox.drafts update --draft-id "268d****50fd" --user-mailbox-id "me" --data '{"raw":"Q29udGVudC1UeXBlOiB0ZXh0L3BsYWluOyBjaGFyc2V0PSJ1cy1hc2NpaSIKTUlNRS1WZXJzaW9uOiAxLjAKQ29udGVudC1UcmFuc2Zlci1FbmNvZGluZzogN2JpdAp0bzogInRvIiA8dG9AeHh4Lnh4Pgpmcm9tOiAiZnJvbSIgPGZyb21AeHh4Lnh4PgpzdWJqZWN0OiB0aGlzIGlzIGEgc3ViamVjdAoKdGhpcyBpcyB0aGUgbWVzc2FnZSBib2R5Lg"}'
```

## user_mailbox.event subscribe
为当前邮箱开启某类事件订阅（如收信事件）

### Avoid when
- 要取消订阅（用 [[user_mailbox.event unsubscribe]]）

### Tips
- event_type 目前可选值为 1

### Examples

**开启收信事件订阅**
```bash
lark-cli mail user_mailbox.event subscribe --user-mailbox-id "me" --data '{"event_type":1}'
```

## user_mailbox.event subscription
查询当前邮箱的事件订阅状态

### Avoid when
- 要开启订阅（用 [[user_mailbox.event subscribe]]）
- 要关闭订阅（用 [[user_mailbox.event unsubscribe]]）

### Examples

**查询事件订阅状态**
```bash
lark-cli mail user_mailbox.event subscription --user-mailbox-id "me"
```

## user_mailbox.event unsubscribe
取消当前邮箱的某类事件订阅

### Avoid when
- 要开启订阅（用 [[user_mailbox.event subscribe]]）

### Tips
- event_type 目前可选值为 1

### Examples

**取消收信事件订阅**
```bash
lark-cli mail user_mailbox.event unsubscribe --user-mailbox-id "me" --data '{"event_type":1}'
```

## user_mailbox.folders create
新建一个邮箱文件夹

### Avoid when
- 要改名或移动已有文件夹（用 [[user_mailbox.folders patch]]）

### Prerequisites
- parent_folder_id 必填，根目录传 "0"，子文件夹的父 id 来自 [[user_mailbox.folders list]]

### Examples

**在根目录新建文件夹**
```bash
lark-cli mail user_mailbox.folders create --user-mailbox-id "me" --data '{"name":"newsletter 相关","parent_folder_id":"0"}'
```

**在指定父文件夹下新建子文件夹**
```bash
lark-cli mail user_mailbox.folders create --user-mailbox-id "me" --data '{"name":"2026 归档","parent_folder_id":"7620****0541"}'
```

## user_mailbox.folders delete
删除一个邮箱文件夹

### Prerequisites
- folder_id 来自 [[user_mailbox.folders list]]

### Examples

**删除文件夹**
```bash
lark-cli mail user_mailbox.folders delete --folder-id "7620****8013" --user-mailbox-id "me"
```

## user_mailbox.folders get
已知 folder_id，查询单个文件夹的详情

### Avoid when
- 还不知道 folder_id（先用 [[user_mailbox.folders list]]）

### Prerequisites
- folder_id 来自 [[user_mailbox.folders list]]

### Examples

**查询单个文件夹详情**
```bash
lark-cli mail user_mailbox.folders get --folder-id "7620****0541" --user-mailbox-id "me"
```

## user_mailbox.folders list
列出邮箱文件夹，拿到 folder_id 供列邮件/移动邮件等使用

### Avoid when
- 已知 folder_id 只查单个文件夹（用 [[user_mailbox.folders get]]）

### Tips
- folder_type 可选：1=系统文件夹，2=用户文件夹；不传返回全部

### Examples

**列出全部文件夹**
```bash
lark-cli mail user_mailbox.folders list --user-mailbox-id "me"
```

**只列用户自建文件夹**
```bash
lark-cli mail user_mailbox.folders list --folder-type "2" --user-mailbox-id "me"
```

## user_mailbox.folders patch
修改已有文件夹的名字或所属父文件夹（移动）

### Avoid when
- 要新建文件夹（用 [[user_mailbox.folders create]]）

### Prerequisites
- folder_id 来自 [[user_mailbox.folders list]]

### Tips
- name 和 parent_folder_id 都可选，按需只传要改的字段；parent_folder_id 传 "0" 移到根目录

### Examples

**重命名文件夹**
```bash
lark-cli mail user_mailbox.folders patch --folder-id "7620****8013" --user-mailbox-id "me" --data '{"name":"newsletter 归档"}'
```

**把文件夹移到根目录**
```bash
lark-cli mail user_mailbox.folders patch --folder-id "7620****8013" --user-mailbox-id "me" --data '{"parent_folder_id":"0"}'
```

## user_mailbox.labels create
新建一个自定义邮件标签

### Avoid when
- 要改已有标签的名字或颜色（用 [[user_mailbox.labels patch]]）

### Tips
- label 是对象，至少含 name，可选 text_color / bg_color

### Examples

**新建标签（仅名称）**
```bash
lark-cli mail user_mailbox.labels create --user-mailbox-id "me" --data '{"label":{"name":"待跟进"}}'
```

**新建带颜色的标签**
```bash
lark-cli mail user_mailbox.labels create --user-mailbox-id "me" --data '{"label":{"name":"待跟进","text_color":"#FFFFFF","bg_color":"#FF0000"}}'
```

## user_mailbox.labels delete
删除一个自定义标签

### Prerequisites
- label_id 来自 [[user_mailbox.labels list]]

### Examples

**删除标签**
```bash
lark-cli mail user_mailbox.labels delete --label-id "7620****8013" --user-mailbox-id "me"
```

## user_mailbox.labels get
已知 label_id，查询单个标签详情

### Avoid when
- 还不知道 label_id（先用 [[user_mailbox.labels list]]）

### Prerequisites
- label_id 来自 [[user_mailbox.labels list]]

### Examples

**查询单个标签详情**
```bash
lark-cli mail user_mailbox.labels get --label-id "7620****8013" --user-mailbox-id "me"
```

## user_mailbox.labels list
列出邮箱标签，拿到 label_id 供按标签筛邮件或打标使用

### Avoid when
- 已知 label_id 只查单个标签（用 [[user_mailbox.labels get]]）

### Examples

**列出全部标签**
```bash
lark-cli mail user_mailbox.labels list --user-mailbox-id "me"
```

## user_mailbox.labels patch
修改已有标签的名字或颜色

### Avoid when
- 要新建标签（用 [[user_mailbox.labels create]]）

### Prerequisites
- label_id 来自 [[user_mailbox.labels list]]

### Tips
- label 是对象，名字与颜色至少填一个

### Examples

**重命名标签**
```bash
lark-cli mail user_mailbox.labels patch --label-id "7620****8013" --user-mailbox-id "me" --data '{"label":{"name":"已跟进"}}'
```

**修改标签颜色**
```bash
lark-cli mail user_mailbox.labels patch --label-id "7620****8013" --user-mailbox-id "me" --data '{"label":{"text_color":"#FFFFFF","bg_color":"#00A870"}}'
```

## user_mailbox.mail_contacts create
新建一个邮箱个人联系人记录

### Avoid when
- 要改已有联系人（用 [[user_mailbox.mail_contacts patch]]）

### Tips
- 仅 name 必填，company/phone/mail_address/position/tag/remark 可选

### Examples

**新建联系人（仅必填名称）**
```bash
lark-cli mail user_mailbox.mail_contacts create --user-mailbox-id "me" --data '{"name":"张三"}'
```

**新建带公司/邮箱/职位的完整联系人**
```bash
lark-cli mail user_mailbox.mail_contacts create --user-mailbox-id "me" --data '{"name":"张三","mail_address":"zhangsan@example.com","company":"张三科技有限公司","position":"CFO","phone":"1991****1234"}'
```

## user_mailbox.mail_contacts delete
删除一个邮箱联系人

### Prerequisites
- mail_contact_id 来自 [[user_mailbox.mail_contacts list]]

### Examples

**删除联系人**
```bash
lark-cli mail user_mailbox.mail_contacts delete --mail-contact-id "123" --user-mailbox-id "me"
```

## user_mailbox.mail_contacts list
列出邮箱个人联系人，拿到 mail_contact_id 供修改/删除使用

### Avoid when
- 写信时搜索联系人补全收件人（用 [[multi_entity search]]）

### Tips
- page_size 必填

### Examples

**列出个人联系人**
```bash
lark-cli mail user_mailbox.mail_contacts list --page-size "20" --user-mailbox-id "me"
```

## user_mailbox.mail_contacts patch
修改已有邮箱联系人的信息

### Avoid when
- 要新建联系人（用 [[user_mailbox.mail_contacts create]]）

### Prerequisites
- mail_contact_id 来自 [[user_mailbox.mail_contacts list]]

### Tips
- name 必填（即使不改也要带上），其余字段按需传

### Examples

**更新联系人电话**
```bash
lark-cli mail user_mailbox.mail_contacts patch --mail-contact-id "123" --user-mailbox-id "me" --data '{"name":"张三","phone":"1991****1234"}'
```

**更新联系人邮箱与备注**
```bash
lark-cli mail user_mailbox.mail_contacts patch --mail-contact-id "123" --user-mailbox-id "me" --data '{"name":"张三","mail_address":"zhangsan@example.com","remark":"飞书发布会认识"}'
```

## user_mailbox.message.attachments download_url
为指定邮件的附件换取下载链接

### Avoid when
- 下载的是邮件模板里的附件（用 [[user_mailbox.template.attachments download_url]]）

### Prerequisites
- message_id 来自 [[user_mailbox.messages list]]；attachment_ids 来自该邮件详情（[[user_mailbox.messages get]]）

### Tips
- attachment_ids 是 id 列表，可一次换多个附件链接

### Examples

**为邮件附件换取下载链接**
```bash
lark-cli mail user_mailbox.message.attachments download_url --attachment-ids "att_001" --message-id "TUlH****Qz0=" --user-mailbox-id "me"
```

**一次为多个附件换取下载链接（重复 --attachment-ids）**
```bash
lark-cli mail user_mailbox.message.attachments download_url --attachment-ids "att_001" --attachment-ids "att_002" --message-id "TUlH****Qz0=" --user-mailbox-id "me"
```

## user_mailbox.messages batch_get
一次性获取多封邮件的详情（传 message_ids 数组）

### Avoid when
- 想读多封邮件的归一化内容、或 ID 超过 20 个 —— 用 [[+messages]]（自动按 20 分批、归一化正文/附件/内联图）；本接口为原始批量 get
- 只取单封（用 [[user_mailbox.messages get]]）

### Prerequisites
- message_ids 来自 [[user_mailbox.messages list]] 或收信事件

### Tips
- format 控制内容样式：full / plain_text_full / metadata

### Examples

**批量获取多封邮件详情**
```bash
lark-cli mail user_mailbox.messages batch_get --user-mailbox-id "me" --data '{"message_ids":["TUlH****Qz0=","NzR3****Qz0="]}'
```

**只取元数据（不含正文）**
```bash
lark-cli mail user_mailbox.messages batch_get --user-mailbox-id "me" --data '{"message_ids":["TUlH****Qz0="],"format":"metadata"}'
```

## user_mailbox.messages batch_modify
一次给多封邮件加/去标签或移动文件夹（传 message_ids 数组）

### Avoid when
- 只改单封（用 [[user_mailbox.messages modify]]）
- 按会话维度批量改（用 [[user_mailbox.threads batch_modify]]）

### Prerequisites
- message_ids 来自 [[user_mailbox.messages list]]

### Tips
- add_label_ids/remove_label_ids 取值含 UNREAD/IMPORTANT/OTHER/FLAGGED 及自定义标签 id；add_folder 支持系统文件夹或自定义文件夹 id

### Examples

**批量标记为已读**
```bash
lark-cli mail user_mailbox.messages batch_modify --user-mailbox-id "me" --data '{"message_ids":["bskfsxxcvve=","TUlH****Qz0="],"remove_label_ids":["UNREAD"]}'
```

**批量移动到归档文件夹**
```bash
lark-cli mail user_mailbox.messages batch_modify --user-mailbox-id "me" --data '{"message_ids":["bskfsxxcvve="],"add_folder":"ARCHIVED"}'
```

## user_mailbox.messages batch_trash
一次把多封邮件移入回收站（传 message_ids 数组）

### Avoid when
- 只删单封（用 [[user_mailbox.messages trash]]）

### Prerequisites
- message_ids 来自 [[user_mailbox.messages list]]

### Examples

**批量把多封邮件移入回收站**
```bash
lark-cli mail user_mailbox.messages batch_trash --user-mailbox-id "me" --data '{"message_ids":["NzR3****Qz0=","bskfsxxcvve="]}'
```

## user_mailbox.messages get
已知 message_id，获取单封邮件的完整详情

### Avoid when
- 只是要读这封邮件的内容（归一化正文、附件与内联图）—— 用 [[+message]]；裸 get 返回原始 format 需自行解析
- 要一次取多封（用 [[user_mailbox.messages batch_get]]）
- 要按会话整体取（用 [[user_mailbox.threads get]]）

### Prerequisites
- message_id 来自 [[user_mailbox.messages list]] 或收信事件

### Tips
- format 控制内容样式：full / plain_text_full / metadata

### Examples

**获取单封邮件完整详情**
```bash
lark-cli mail user_mailbox.messages get --message-id "TUlH****Qz0=" --user-mailbox-id "me"
```

**只取纯文本正文（format 与 CLI 输出 --format 同名，走 --params）**
```bash
lark-cli mail user_mailbox.messages get --message-id "TUlH****Qz0=" --params '{"format":"plain_text_full"}' --user-mailbox-id "me"
```

## user_mailbox.messages list
按文件夹/标签/未读状态分页列出单封邮件，拿到 message_id

### Avoid when
- 想要可读的邮件摘要清单（date/from/subject/message_id）—— 用 [[+triage]]（还支持 --query 全文搜、--filter 精筛）；裸 list 返回原始字段需自行投影
- 想按关键词检索（用 [[user_mailboxes search]]）
- 要按会话维度列出而非单封（用 [[user_mailbox.threads list]]）

### Tips
- page_size 必填
- folder_id 支持 INBOX/SENT/SPAM/ARCHIVED 等系统值或自定义文件夹 id；label_id 支持 IMPORTANT/OTHER/FLAGGED 等

### Examples

**列出收件箱邮件**
```bash
lark-cli mail user_mailbox.messages list --page-size "20" --user-mailbox-id "me"
```

**只看某文件夹的未读邮件**
```bash
lark-cli mail user_mailbox.messages list --page-size "20" --folder-id "INBOX" --only-unread --user-mailbox-id "me"
```

## user_mailbox.messages modify
给单封邮件加/去标签或移动到指定文件夹

### Avoid when
- 要一次改多封（用 [[user_mailbox.messages batch_modify]]）
- 要对整个会话操作（用 [[user_mailbox.threads modify]]）
- 要删邮件（用 [[user_mailbox.messages trash]]）

### Prerequisites
- message_id 来自 [[user_mailbox.messages list]]

### Tips
- add_label_ids/remove_label_ids 取值含 UNREAD/IMPORTANT/OTHER/FLAGGED 及自定义标签 id；add_folder 支持 INBOX/SENT/SPAM/ARCHIVED 或自定义文件夹 id

### Examples

**标记邮件为已读**
```bash
lark-cli mail user_mailbox.messages modify --message-id "bskfsxxcvve=" --user-mailbox-id "me" --data '{"remove_label_ids":["UNREAD"]}'
```

**给邮件打自定义标签**
```bash
lark-cli mail user_mailbox.messages modify --message-id "bskfsxxcvve=" --user-mailbox-id "me" --data '{"add_label_ids":["7620****8013"]}'
```

**把邮件移动到指定文件夹**
```bash
lark-cli mail user_mailbox.messages modify --message-id "bskfsxxcvve=" --user-mailbox-id "me" --data '{"add_folder":"ARCHIVED"}'
```

## user_mailbox.messages send_status
查询某封已发邮件的投递/发送状态

### Avoid when
- 要查撤回进度（用 [[user_mailbox.sent_messages get_recall_detail]]）

### Prerequisites
- message_id 是邮件的业务标识 message_biz_id（发信结果返回）

### Examples

**查询已发邮件的投递状态**
```bash
lark-cli mail user_mailbox.messages send_status --message-id "197c****1d78" --user-mailbox-id "me"
```

## user_mailbox.messages trash
把单封邮件移入回收站（删除）

### Avoid when
- 要一次删多封（用 [[user_mailbox.messages batch_trash]]）
- 要删整个会话（用 [[user_mailbox.threads trash]]）

### Prerequisites
- message_id 来自 [[user_mailbox.messages list]]

### Examples

**把单封邮件移入回收站**
```bash
lark-cli mail user_mailbox.messages trash --message-id "NzR3****Qz0=" --user-mailbox-id "me"
```

## user_mailbox.rules create
新建一条收信规则（命中条件后自动执行打标/移动等操作）

### Avoid when
- 要改已有规则（用 [[user_mailbox.rules update]]）
- 只是调整规则执行顺序（用 [[user_mailbox.rules reorder]]）

### Tips
- condition 与 action 都是对象；ignore_the_rest_of_rules 为 true 时命中后终止后续规则

### Examples

**新建规则：命中发件人则标记为垃圾邮件**
```bash
lark-cli mail user_mailbox.rules create --user-mailbox-id "me" --data '{"name":"将李三的邮件标记为垃圾邮件","is_enable":true,"ignore_the_rest_of_rules":false,"condition":{"match_type":1,"items":[{"type":1,"operator":3,"input":"lisan@example.com"}]},"action":{"items":[{"type":4}]}}'
```

## user_mailbox.rules delete
删除一条收信规则

### Prerequisites
- rule_id 来自 [[user_mailbox.rules list]]

### Examples

**删除一条收信规则**
```bash
lark-cli mail user_mailbox.rules delete --rule-id "123123123" --user-mailbox-id "me"
```

## user_mailbox.rules list
列出收信规则，拿到 rule_id 供更新/删除/排序使用

### Examples

**列出收信规则**
```bash
lark-cli mail user_mailbox.rules list --user-mailbox-id "me"
```

## user_mailbox.rules reorder
调整多条收信规则的执行优先级顺序

### Avoid when
- 要改规则内容（用 [[user_mailbox.rules update]]）

### Prerequisites
- rule_ids 来自 [[user_mailbox.rules list]]

### Tips
- rule_ids 是数组，按期望的执行先后顺序传入全部规则 id

### Examples

**按期望顺序重排收信规则**
```bash
lark-cli mail user_mailbox.rules reorder --user-mailbox-id "me" --data '{"rule_ids":["123123123","456456456"]}'
```

## user_mailbox.rules update
全量更新一条已有收信规则的条件/动作/开关

### Avoid when
- 要新建规则（用 [[user_mailbox.rules create]]）
- 只调整规则顺序（用 [[user_mailbox.rules reorder]]）

### Prerequisites
- rule_id 来自 [[user_mailbox.rules list]]

### Tips
- 为全量更新，所有必填字段（name/is_enable/condition/action/ignore_the_rest_of_rules）都要带上

### Examples

**全量更新一条收信规则**
```bash
lark-cli mail user_mailbox.rules update --rule-id "123123123" --user-mailbox-id "me" --data '{"name":"将李三的邮件标记为垃圾邮件","is_enable":true,"ignore_the_rest_of_rules":false,"condition":{"match_type":1,"items":[{"type":1,"operator":3,"input":"lisan@example.com"}]},"action":{"items":[{"type":4}]}}'
```

## user_mailbox.sent_messages get_recall_detail
查询某封邮件的撤回进度/结果

### Avoid when
- 要查的是普通发送状态（用 [[user_mailbox.messages send_status]]）

### Prerequisites
- message_id 为已调用过 [[user_mailbox.sent_messages recall]] 的邮件 id

### Examples

**查询邮件撤回进度**
```bash
lark-cli mail user_mailbox.sent_messages get_recall_detail --message-id "197c****1d78" --user-mailbox-id "me"
```

## user_mailbox.sent_messages recall
撤回一封已发送的邮件

### Avoid when
- 邮件尚未发出、只是定时待发（用 [[user_mailbox.drafts cancel_scheduled_send]]）

### Prerequisites
- message_id 为已发送邮件的 id（来自 [[user_mailbox.drafts send]] 的结果）

### Tips
- 撤回是异步过程，结果用 [[user_mailbox.sent_messages get_recall_detail]] 查询

### Examples

**撤回一封已发送的邮件**
```bash
lark-cli mail user_mailbox.sent_messages recall --message-id "197c****1d78" --user-mailbox-id "me"
```

## user_mailbox.settings send_as
列出该邮箱可用作发信地址的身份（主地址及别名），用于确定草稿/邮件的 From

### Avoid when
- 要列可访问的其他邮箱（用 [[user_mailboxes accessible_mailboxes]]）

### Examples

**列出可用作发信地址的身份**
```bash
lark-cli mail user_mailbox.settings send_as --user-mailbox-id "me"
```

## user_mailbox.template.attachments download_url
为指定邮件模板的附件换取下载链接

### Avoid when
- 下载的是邮件本身的附件（用 [[user_mailbox.message.attachments download_url]]）

### Prerequisites
- template_id 来自 [[user_mailbox.templates list]]；attachment_ids 来自该模板详情（[[user_mailbox.templates get]]）

### Tips
- attachment_ids 是 id 列表，可一次换多个附件链接

### Examples

**为模板附件换取下载链接**
```bash
lark-cli mail user_mailbox.template.attachments download_url --attachment-ids "att_001" --template-id "7281****2947" --user-mailbox-id "me"
```

## user_mailbox.templates create
新建一个个人邮件模板

### Avoid when
- 模板正文含本地内联图/附件 —— 用 [[+template-create]]，它自动上传图片并把 <img> 改写为 cid: 引用；裸 create 需自备拼好的 template 对象
- 要改已有模板（用 [[user_mailbox.templates update]]）

### Tips
- template 是对象，含模板名称与正文等内容

### Examples

**新建邮件模板**
```bash
lark-cli mail user_mailbox.templates create --user-mailbox-id "me" --data '{"template":{"name":"周报模板","body_html":"本周进展..."}}'
```

## user_mailbox.templates delete
删除一个邮件模板

### Prerequisites
- template_id 来自 [[user_mailbox.templates list]]

### Examples

**删除邮件模板**
```bash
lark-cli mail user_mailbox.templates delete --template-id "7281****2947" --user-mailbox-id "me"
```

## user_mailbox.templates get
已知 template_id，获取单个邮件模板的完整内容

### Avoid when
- 只需要 id 与名称列表（用 [[user_mailbox.templates list]]）

### Prerequisites
- template_id 来自 [[user_mailbox.templates list]]

### Examples

**获取单个模板完整内容**
```bash
lark-cli mail user_mailbox.templates get --template-id "7281****2947" --user-mailbox-id "me"
```

## user_mailbox.templates list
列出该邮箱下全部个人邮件模板，拿到 template_id（不分页，仅返回 id 与 name）

### Avoid when
- 已知 template_id 要看完整内容（用 [[user_mailbox.templates get]]）

### Examples

**列出全部邮件模板**
```bash
lark-cli mail user_mailbox.templates list --user-mailbox-id "me"
```

## user_mailbox.templates update
全量替换已有邮件模板的内容

### Avoid when
- 想增量改模板或正文含本地图片 —— 用 [[+template-update]]，支持 --inspect/flat flags 并自动把 <img> 改写为 cid: 引用；裸 update 是全量替换，需自备完整 template 对象
- 要新建模板（用 [[user_mailbox.templates create]]）

### Prerequisites
- template_id 来自 [[user_mailbox.templates list]]

### Tips
- template 是对象，为全量替换，需提供完整内容

### Examples

**全量替换模板内容**
```bash
lark-cli mail user_mailbox.templates update --template-id "7281****2947" --user-mailbox-id "me" --data '{"template":{"name":"周报模板","body_html":"更新后的内容..."}}'
```

## user_mailbox.threads batch_modify
一次给多个会话加/去标签或移动文件夹（传 thread_ids 数组）

### Avoid when
- 只改单个会话（用 [[user_mailbox.threads modify]]）
- 按单封邮件维度批量改（用 [[user_mailbox.messages batch_modify]]）

### Prerequisites
- thread_ids 来自 [[user_mailbox.threads list]]

### Tips
- add_label_ids/remove_label_ids 取值含 UNREAD/IMPORTANT/OTHER/FLAGGED 及自定义标签 id；add_folder 支持系统文件夹或自定义文件夹 id

### Examples

**批量标记会话为已读**
```bash
lark-cli mail user_mailbox.threads batch_modify --user-mailbox-id "me" --data '{"thread_ids":["th_xxxxxxxxxxxx","th_yyyyyyyyyyyy"],"remove_label_ids":["UNREAD"]}'
```

**批量把会话移到归档文件夹**
```bash
lark-cli mail user_mailbox.threads batch_modify --user-mailbox-id "me" --data '{"thread_ids":["th_xxxxxxxxxxxx"],"add_folder":"ARCHIVED"}'
```

## user_mailbox.threads batch_trash
一次把多个会话移入回收站（传 thread_ids 数组）

### Avoid when
- 只删单个会话（用 [[user_mailbox.threads trash]]）
- 按单封邮件维度删（用 [[user_mailbox.messages batch_trash]]）

### Prerequisites
- thread_ids 来自 [[user_mailbox.threads list]]

### Examples

**批量把多个会话移入回收站**
```bash
lark-cli mail user_mailbox.threads batch_trash --user-mailbox-id "me" --data '{"thread_ids":["th_xxxxxxxxxxxx","th_yyyyyyyyyyyy"]}'
```

## user_mailbox.threads get
已知 thread_id，获取整个邮件会话的详情（含会话内多封邮件）

### Avoid when
- 想读整条会话的可读内容 —— 用 [[+thread]]，它按时间顺序归一化会话内所有邮件正文与附件（含内联图）
- 只要会话里某一封邮件（用 [[user_mailbox.messages get]]）

### Prerequisites
- thread_id 来自 [[user_mailbox.threads list]] 或邮件详情

### Tips
- include_spam_trash=true 时也返回 SPAM/TRASH 中的邮件；format 控制内容样式 full/plain_text_full/metadata

### Examples

**获取整个会话详情**
```bash
lark-cli mail user_mailbox.threads get --thread-id "th_xxxxxxxxxxxx" --user-mailbox-id "me"
```

**含垃圾箱/回收站的会话**
```bash
lark-cli mail user_mailbox.threads get --thread-id "th_xxxxxxxxxxxx" --include-spam-trash --user-mailbox-id "me"
```

## user_mailbox.threads list
按会话（thread）维度分页列出邮件，可按文件夹/标签/未读筛选，拿到 thread_id

### Avoid when
- 想要单封邮件粒度（用 [[user_mailbox.messages list]]）
- 想按关键词检索（用 [[user_mailboxes search]]）

### Tips
- page_size 必填
- folder_id 还支持 SCHEDULED/TRASH/DRAFT 等系统值

### Examples

**列出会话**
```bash
lark-cli mail user_mailbox.threads list --page-size "20" --user-mailbox-id "me"
```

**只看收件箱里的未读会话**
```bash
lark-cli mail user_mailbox.threads list --page-size "20" --folder-id "INBOX" --only-unread --user-mailbox-id "me"
```

## user_mailbox.threads modify
给单个会话加/去标签或整体移动到指定文件夹

### Avoid when
- 要一次改多个会话（用 [[user_mailbox.threads batch_modify]]）
- 只对单封邮件操作（用 [[user_mailbox.messages modify]]）

### Prerequisites
- thread_id 来自 [[user_mailbox.threads list]]

### Tips
- add_label_ids/remove_label_ids 取值含 UNREAD/IMPORTANT/OTHER/FLAGGED 及自定义标签 id；add_folder 支持系统文件夹或自定义文件夹 id

### Examples

**标记会话为已读**
```bash
lark-cli mail user_mailbox.threads modify --thread-id "th_xxxxxxxxxxxx" --user-mailbox-id "me" --data '{"remove_label_ids":["UNREAD"]}'
```

**把会话整体移到归档文件夹**
```bash
lark-cli mail user_mailbox.threads modify --thread-id "th_xxxxxxxxxxxx" --user-mailbox-id "me" --data '{"add_folder":"ARCHIVED"}'
```

## user_mailbox.threads trash
把单个会话移入回收站（删除）

### Avoid when
- 要一次删多个会话（用 [[user_mailbox.threads batch_trash]]）
- 只删会话里的某一封邮件（用 [[user_mailbox.messages trash]]）

### Prerequisites
- thread_id 来自 [[user_mailbox.threads list]]

### Examples

**把单个会话移入回收站**
```bash
lark-cli mail user_mailbox.threads trash --thread-id "th_xxxxxxxxxxxx" --user-mailbox-id "me"
```

## user_mailboxes accessible_mailboxes
列出当前用户可访问的邮箱（如被授权的共享/他人邮箱），用于确定后续接口该传哪个 user_mailbox_id

### Avoid when
- 要查当前邮箱本身的资料信息（用 [[user_mailboxes profile]]）
- 要列可作为发信地址的别名（用 [[user_mailbox.settings send_as]]）

### Prerequisites
- 不可用公共邮箱地址调用此接口

### Examples

**列出当前用户可访问的邮箱**
```bash
lark-cli mail user_mailboxes accessible_mailboxes --user-mailbox-id "me"
```

## user_mailboxes profile
获取用户邮箱的资料信息（如邮箱地址、容量等）

### Avoid when
- 要列出可访问的其他邮箱（用 [[user_mailboxes accessible_mailboxes]]）

### Prerequisites
- user_mailbox_id 只支持填 me

### Examples

**获取当前邮箱资料信息**
```bash
lark-cli mail user_mailboxes profile --user-mailbox-id "me"
```

## user_mailboxes search
在邮箱内按关键词全文搜索邮件，可用 filter 按发件人/收件人/文件夹/时间/未读等组合精筛

### Avoid when
- 想要可读的搜索结果摘要 —— 用 [[+triage --query]]（全文搜，返回 date/from/subject/message_id 摘要）；本接口返回原始结果、支持更细的 filter 对象
- 只想按文件夹/标签/未读顺序列邮件而非关键词检索（用 [[user_mailbox.messages list]] 或 [[user_mailbox.threads list]]）
- 搜的是写信联系人而非邮件（用 [[multi_entity search]]）

### Tips
- filter 是对象，如 {"from":["user@example.com"],"is_unread":true}
- page_size 默认 15，范围 1-15；翻页传 page_token

### Examples

**按关键词全文搜索邮件**
```bash
lark-cli mail user_mailboxes search --user-mailbox-id "me" --data '{"query":"合同审批通知"}'
```

**按发件人+未读组合精筛**
```bash
lark-cli mail user_mailboxes search --user-mailbox-id "me" --data '{"query":"合同审批通知","filter":{"from":["boss@example.com"],"is_unread":true}}'
```

**搜索并翻页**
```bash
lark-cli mail user_mailboxes search --user-mailbox-id "me" --page-size "15" --page-token "xxx" --data '{"query":"合同审批通知"}'
```
