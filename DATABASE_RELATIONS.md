# SmartStay 数据库表关系文档

## 表关系总览

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   users     │────<│   orders    │>────│   rooms     │
│  (住客/员工) │     │   (订单)    │     │   (房间)    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │                   │                   │
       │              ┌────┴────┐         ┌────┴────┐
       │              │         │         │         │
       │         ┌────┴────┐ ┌──┴───┐ ┌───┴──┐ ┌───┴────┐
       │         │work_    │ │consum│ │chat_ │ │ai_     │
       │         │orders   │ │ption │ │sess  │ │security│
       │         └─────────┘ └──────┘ └──┬───┘ └────────┘
       │                                 │
       │                            ┌────┴────┐
       │                            │chat_    │
       │                            │messages │
       │                            └─────────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
  ┌────┴────┐                             ┌──────┴──────┐
  │rag_     │                             │ai_pricing_  │
  │documents│                             │logs         │
  └────┬────┘                             └─────────────┘
       │
  ┌────┴────┐
  │rag_     │
  │embeddings│
  └─────────┘
```

## 详细表结构与关系

### 1. users (用户表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| id_card | VARCHAR(18) | 身份证号（唯一） |
| phone | VARCHAR(11) | 手机号 |
| name | VARCHAR(50) | 姓名 |
| hashed_password | VARCHAR(255) | 密码哈希 |
| is_first_login | BOOLEAN | 是否首次登录 |
| is_active | BOOLEAN | 账号是否激活（退房后=false） |
| role | VARCHAR(20) | 角色：guest/front_desk/manager/admin |
| created_at | TIMESTAMP | 创建时间 |

**当前数据：** 10个用户

| 姓名 | 身份证号 | 角色 | is_active |
|------|----------|------|-----------|
| 总店长 | dianzhang | manager | true |
| 前台张 | qiantai | front_desk | true |
| 管理员 | admin | admin | true |
| 住客李 | 100000000000000101 | guest | true |
| invoice_test | 429005199001011240 | guest | true |
| 康烜航 | 13042920030603401X | guest | true |
| test_checkin | 429005199001011237 | guest | false |
| 宋洁 | 18003306325 | guest | false |
| 康烜航 | 1111 | guest | false |
| 宋洁 | 123456789 | guest | false |

---

### 2. rooms (房间表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| room_number | VARCHAR(10) | 房间号（唯一） |
| room_type | VARCHAR(20) | 房型：big_bed/twin/suite |
| base_price | INT | 基础价格（分） |
| current_price | INT | 当前价格（分） |
| status | VARCHAR(20) | 状态：vacant/occupied/dirty/maintenance |
| device_states | JSONB | 设备状态（灯光/窗帘/空调） |
| floor | INT | 楼层 |

**当前数据：** 10个房间，全部 vacant

| 房间号 | 房型 | 楼层 | 基础价 | 当前价 |
|--------|------|------|--------|--------|
| 301 | 大床房 | 3 | ¥300 | ¥300 |
| 302 | 大床房 | 3 | ¥300 | ¥300 |
| 303 | 双床房 | 3 | ¥350 | ¥350 |
| 304 | 双床房 | 3 | ¥350 | ¥350 |
| 305 | 套房 | 3 | ¥600 | ¥600 |
| 401 | 大床房 | 4 | ¥320 | ¥320 |
| 402 | 大床房 | 4 | ¥320 | ¥320 |
| 403 | 双床房 | 4 | ¥370 | ¥370 |
| 404 | 套房 | 4 | ¥660 | ¥660 |
| 501 | 套房 | 5 | ¥720 | ¥720 |

---

### 3. orders (订单表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID (FK) | 关联 users.id |
| room_id | UUID (FK) | 关联 rooms.id |
| status | VARCHAR(20) | 状态：pending/checked_in/checked_out |
| source | VARCHAR(20) | 来源：self_app/front_desk/ctrip/meituan |
| check_in_time | TIMESTAMP | 入住时间 |
| check_out_time | TIMESTAMP | 退房时间 |
| total_amount | INT | 总金额（分） |
| created_at | TIMESTAMP | 创建时间 |

**关系：**
- `orders.user_id` → `users.id` (一个用户可以有多个订单)
- `orders.room_id` → `rooms.id` (一个房间可以有多个订单，但同一时间只有一个 checked_in)

**当前数据：** 20条订单

| 订单ID | 用户 | 房间 | 状态 | 来源 | 入住时间 | 退房时间 |
|--------|------|------|------|------|----------|----------|
| e5408c97... | 宋洁(123456789) | 301 | checked_out | self_app | 2026-05-27 03:04 | 2026-05-27 03:04 |
| d870a368... | 康烜航(130429...) | 302 | checked_out | ctrip | 2026-05-27 02:52 | 2026-05-27 03:04 |
| 5418244d... | 康烜航(130429...) | 302 | checked_in | ctrip | 2026-05-27 02:51 | - |
| 00e9c534... | 康烜航(1111) | 401 | checked_out | meituan | 2026-05-27 02:24 | 2026-05-27 02:45 |
| a431b606... | 康烜航(130429...) | 403 | checked_out | self_app | 2026-05-27 02:02 | 2026-05-27 02:45 |
| 9f4d1b30... | 宋洁(180033...) | 403 | checked_out | self_app | 2026-05-27 01:32 | 2026-05-27 02:01 |
| abaa0937... | invoice_test | 301 | checked_in | self_app | 2026-05-26 06:25 | - |
| ... | ... | ... | ... | ... | ... | ... |

---

### 4. work_orders (工单表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| room_id | UUID (FK) | 关联 rooms.id |
| order_id | UUID (FK) | 关联 orders.id（可为空） |
| type | VARCHAR(20) | 类型：repair/cleaning/amenity |
| content | TEXT | 工单内容 |
| assigned_resource | VARCHAR(50) | 指派人员 |
| status | VARCHAR(20) | 状态：submitted/accepted/processing/completed |
| ai_generated | BOOLEAN | 是否AI生成 |
| created_at | TIMESTAMP | 创建时间 |

**关系：**
- `work_orders.room_id` → `rooms.id` (一个房间可以有多个工单)
- `work_orders.order_id` → `orders.id` (可选关联)

**当前数据：** 27条工单，全部是301房的"马桶堵塞，需要维修"

| 工单数 | 房间 | 类型 | 内容 | 状态 | AI生成 |
|--------|------|------|------|------|--------|
| 27 | 301 | repair | 马桶堵塞，需要维修 | accepted | true |

---

### 5. consumptions (消费表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| order_id | UUID (FK) | 关联 orders.id |
| room_id | UUID (FK) | 关联 rooms.id |
| item_name | VARCHAR(50) | 消费项目名 |
| category | VARCHAR(20) | 分类：minibar/restaurant/laundry |
| amount | INT | 单价（分） |
| quantity | INT | 数量 |
| consumed_at | TIMESTAMP | 消费时间 |

**关系：**
- `consumptions.order_id` → `orders.id` (一个订单可以有多条消费)
- `consumptions.room_id` → `rooms.id`

**当前数据：** 0条记录

---

### 6. invoice_records (发票表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| order_id | UUID (FK) | 关联 orders.id |
| company_name | VARCHAR(100) | 公司名称 |
| tax_id | VARCHAR(20) | 税号 |
| email | VARCHAR(100) | 邮箱 |
| status | VARCHAR(20) | 状态：draft/issued |

**关系：**
- `invoice_records.order_id` → `orders.id` (一个订单可以有一个发票)

**当前数据：** 27条发票记录

| 发票数 | 公司名 | 税号 | 状态 |
|--------|--------|------|------|
| 26 | 测试公司 | 91110000TEST | draft |
| 1 | 测试公司 | 91110000TEST | issued |

---

### 7. ai_pricing_logs (AI定价日志)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| room_type | VARCHAR(20) | 房型 |
| trigger_reason | VARCHAR(100) | 触发原因 |
| original_price | INT | 原价（分） |
| suggested_price | INT | 建议价（分） |
| status | VARCHAR(20) | 状态：pending/approved/rejected |
| confirmed_by | UUID (FK) | 确认人（关联 users.id） |

**当前数据：** 1条记录

| 房型 | 触发原因 | 原价 | 建议价 | 状态 |
|------|----------|------|--------|------|
| 大床房 | venue overflow event | ¥320 | ¥420 | pending |

---

### 8. audit_reports (审计报告)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| date | DATE | 审计日期 |
| content | JSONB | 报告内容 |
| anomalies | JSONB | 异常信息 |

**当前数据：** 0条记录

---

### 9. ai_security_logs (AI安全日志)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID (FK) | 关联 users.id |
| room_id | UUID (FK) | 关联 rooms.id |
| role | VARCHAR(20) | 用户角色 |
| tool_name | VARCHAR(50) | 工具名称 |
| tool_params | JSONB | 工具参数 |
| violation_type | VARCHAR(50) | 违规类型：ROLE_VIOLATION/PRICE_LIMIT/PARAM_ABUSE |
| user_input | TEXT | 用户输入 |
| created_at | TIMESTAMP | 创建时间 |

**当前数据：** 0条记录

---

### 10. rag_documents (RAG文档表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| title | VARCHAR(100) | 文档标题 |
| file_name | VARCHAR(100) | 文件名 |
| content | TEXT | 文档内容 |
| chunks | INT | 切片数量 |
| uploaded_by | UUID (FK) | 上传人（关联 users.id） |
| created_at | TIMESTAMP | 上传时间 |

**关系：**
- `rag_documents.uploaded_by` → `users.id` (谁上传的)

**当前数据：** 2条记录

| 标题 | 文件名 | 切片数 | 上传人 |
|------|--------|--------|--------|
| pool_test | pool.md | 1 | - |
| 智宿云大酒店服务完全手册.md | 智宿云大酒店服务完全手册.md | 11 | 总店长 |

---

### 11. rag_embeddings (RAG向量表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| document_id | UUID (FK) | 关联 rag_documents.id |
| chunk_index | INT | 切片序号 |
| content | TEXT | 切片内容 |
| embedding | Vector(512) | 向量嵌入 |

**关系：**
- `rag_embeddings.document_id` → `rag_documents.id` (一个文档有多个切片)

---

### 12. chat_sessions (聊天会话表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| order_id | UUID (FK) | 关联 orders.id |
| room_id | UUID (FK) | 关联 rooms.id |
| status | VARCHAR(20) | 状态：active/closed |

**关系：**
- `chat_sessions.order_id` → `orders.id` (一个订单可以有一个聊天会话)
- `chat_sessions.room_id` → `rooms.id`

**当前数据：** 3个会话，全部关联301房

---

### 13. chat_messages (聊天消息表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| session_id | UUID (FK) | 关联 chat_sessions.id |
| role | VARCHAR(20) | 角色：user/assistant/system |
| content | TEXT | 消息内容 |
| tool_calls | JSONB | 工具调用记录 |
| created_at | TIMESTAMP | 创建时间 |

**关系：**
- `chat_messages.session_id` → `chat_sessions.id` (一个会话有多条消息)

**当前数据：** 10条消息

| 会话ID | 角色 | 内容摘要 |
|--------|------|----------|
| 9c1dd49b... | user | hello |
| 9c1dd49b... | assistant | chatHello! Welcome to Zhisu Cloud Hotel... |
| b331fe2b... | user | pool open hours |
| b331fe2b... | assistant | knowledge根据酒店知识库信息... |
| 64638d90... | user | 你是谁 |
| 64638d90... | assistant | chat您好，我是智宿云酒店的AI虚拟管家... |

---

### 14. hotel_info (酒店信息表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(100) | 酒店名称 |
| address | VARCHAR(200) | 地址 |
| phone | VARCHAR(20) | 电话 |
| map_lat | FLOAT | 纬度 |
| map_lng | FLOAT | 经度 |
| description | TEXT | 描述 |
| banner_images | JSONB | 轮播图片URL |

**当前数据：** 1条记录

| 名称 | 地址 | 电话 |
|------|------|------|
| 智宿云酒店 | 北京市朝阳区建国路88号SOHO现代城 | 13800000002 |

---

### 15. facilities (设施表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(50) | 设施名称 |
| type | VARCHAR(20) | 类型：gym/pool/restaurant/laundry |
| open_time | TIME | 开放时间 |
| close_time | TIME | 关闭时间 |
| is_free | BOOLEAN | 是否免费 |
| price | INT | 价格（分） |
| dynamic_tip | JSONB | 动态提示 |

**当前数据：** 4个设施

| 名称 | 类型 | 开放时间 | 免费 |
|------|------|----------|------|
| 24H健身房 | gym | 00:00-23:59 | true |
| 无边际泳池 | pool | 08:00-22:00 | true |
| 中餐厅·悦府 | restaurant | 11:00-22:00 | false |
| 自助洗衣房 | laundry | 00:00-23:59 | true |

---

## 关键业务流程关系图

### 入住流程
```
用户登录(users) → 前台办理入住(orders) → 房间状态更新(rooms)
                    ↓
              创建订单(status=checked_in)
                    ↓
              用户激活(is_active=true)
```

### 退房流程
```
前台退房(orders) → 房间状态变dirty(rooms) → 检查用户是否有其他订单
                                              ↓
                                    无其他订单 → 用户停用(is_active=false)
                                    有其他订单 → 用户保持激活
```

### AI聊天流程
```
C端用户 → 创建聊天会话(chat_sessions) → 发送消息(chat_messages)
                                            ↓
                                    AI调用工具(tool_calls)
                                            ↓
                                    查询知识库(rag_embeddings) → 返回结果
```

### 工单流程
```
客人/AI创建工单(work_orders) → 前台接单 → 指派人员 → 完成
                                    ↓
                              WebSocket推送通知
```

---

## 数据统计

| 表名 | 记录数 | 说明 |
|------|--------|------|
| users | 10 | 4个员工 + 6个住客 |
| rooms | 10 | 全部vacant |
| orders | 20 | 2个checked_in + 18个checked_out |
| work_orders | 27 | 全部是301房的维修工单 |
| consumptions | 0 | 无消费记录 |
| invoice_records | 27 | 26个draft + 1个issued |
| ai_pricing_logs | 1 | 1个pending |
| audit_reports | 0 | 无审计报告 |
| ai_security_logs | 0 | 无安全违规 |
| rag_documents | 2 | 2个知识库文档 |
| rag_embeddings | 12 | 12个向量切片 |
| chat_sessions | 3 | 3个聊天会话 |
| chat_messages | 10 | 10条聊天消息 |
| hotel_info | 1 | 1条酒店信息 |
| facilities | 4 | 4个设施 |
