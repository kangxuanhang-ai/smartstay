# 房费多日计算与营收统计优化设计说明书

**日期**：2026-06-04
**范围**：后端 pi/orders.py（账单计算）、pi/admin.py（大盘统计）、schemas/order.py、core/utils.py
**依赖**：F001（后端核心）、F002（B端前端）

---

## 现状分析

### 当前计费逻辑
- Order.total_amount 在入住时写入，值为单日房价（如 72000 分 = ¥720/晚）
- GET /api/orders/{id}/bill 直接返回 order.total_amount 作为 
oom_rate，不管住了几天
- get_bill_total() 也直接用 order.total_amount + consumption_total

### 当前大盘统计逻辑
- GET /api/admin/dashboard：今日流水 = SUM(total_amount) WHERE check_in_time.date() == today
  - 只统计今天新入住的订单，续住房今天不算收入
- GET /api/admin/hourly-revenue：同理只看 check_in_time，不考虑续住

### 已确认的 Bug
| # | 问题 | 举例 |
|---|------|------|
| 1 | 账单房费是死数，不随天数增长 | 501房住了2天（6/2入住），账单仍显示¥720 |
| 2 | 店长今日流水漏算续住房 | 昨天入住¥320房，今天还在住，今日流水不计¥320 |
| 3 | 小时流水走势只统计新入住 | 续住房不在今日走势中体现（保持不变，仅统计新入住） |

---

## 优化方案

### 核心设计决策
- 	otal_amount **永远不改**，始终是单日房价（分）。退房后也不覆盖。
- 账单接口**动态计算**：
oom_rate = total_amount × nights，
ights 从 check_in_time → 
ow/check_out_time 算出
- 大盘今日流水用 **Room.base_price** 作为单日房价，不依赖 	otal_amount
- 不改 Order 模型，不加字段，零数据库迁移

### 1. 新增通用计算函数
**文件：** ackend/app/core/utils.py

新增 calculate_nights(check_in_time, check_out_time=None) 函数：
- 参数：check_in_time: datetime, check_out_time: Optional[datetime]
- 如果 check_out_time 为 None（未退房），用 cst_now() 替代
- 计算 delta = end - check，
ights = max(1, ceil(delta.total_seconds() / 86400))
- 返回 
ights: int，最少为 1
- 酒店行业惯例：入住当天算 1 晚

### 2. 修复账单接口
**文件：** ackend/app/api/orders.py

**get_bill 接口改动：**
- 调用 calculate_nights(order.check_in_time, order.check_out_time) 计算住夜晚数
- BillResponse.room_rate 返回**多日累计房费** = order.total_amount × nights
- 新增返回字段：
ights: int（住夜晚数）、daily_rate: int（单日房价）
- grand_total = 多日房费 + consumption_total

**get_bill_total 函数改动：**
- 同样调用 calculate_nights，返回 	otal_amount × nights + consumption_total

**BillResponse schema 改动：**
- 新增字段：
ights: int = 1、daily_rate: int = 0
- 
oom_rate 语义变为"房费小计（多日累计）"

### 3. 退房逻辑不变
**文件：** ackend/app/api/orders.py

checkout 接口**不改** 	otal_amount。退房只改 status 和 check_out_time。	otal_amount 始终是单日房价。

### 4. 修复大盘今日流水
**文件：** ackend/app/api/admin.py

**get_dashboard 改动：**
- 预加载 
oom_prices = {str(r.id): r.base_price for r in rooms}
- 查所有 check_in_time 非空的订单（checked_in + checked_out + completed）
- 对每个订单判断"今天是否在住"：check_in_time.date() <= today AND (check_out_time is None OR check_out_time.date() >= today)
- 今天在住 → 计入今日流水 += room_prices[room_id]（每天 1 晚）
- 入住数（occupied）= 今天在住的去重房间数
- RevPAR = 今日流水 / 总房间数

**hourly-revenue 改动：**
- **保持现有逻辑不变**：只按新入住时间统计小时分布
- 续住房收入体现在"今日流水"总数里，不拆到小时维度
- 避免图表上出现"凌晨收入异常集中"的误导

### 5. 前端无需改动
- C端账单页 ill_page.dart / ill_detail_page.dart：用 grand_total / 100 显示，字段名不变
- B端 DashboardPage.tsx：用 stats.revenue / 100 显示，字段名不变
- B端房间详情弹窗：走 GET /api/orders/{id}/bill，自动获得正确的多日累计值

---

## 不改动项

- Order 模型：	otal_amount 字段不变，语义始终为单日房价
- C端 Flutter：账单页面无需改动
- B端 React：大盘页面无需改动
- 支付宝支付：lipay.py 的金额来自 get_bill_total()，会自动获得正确的多日金额
- 数据库：零迁移

---

## 验证方式

| 场景 | 预期结果 |
|------|----------|
| 501房6/2入住¥720/晚，6/4查看账单 | room_rate = ¥720 × 2 = ¥1440，nights=2，daily_rate=720 |
| 501房6/2入住，6/4退房后查账单 | 同上，bill接口动态算，total_amount仍是72000 |
| 店长今日流水：昨天入住¥320房今天还在住 | 今日流水包含¥320 |
| 店长今日流水：今天新入住¥600房 | 今日流水包含¥600 |
| 小时流水：只统计新入住 | 续住房不体现在小时走势中 |
| py_compile | 通过 |
| tsc --noEmit | 通过 |
