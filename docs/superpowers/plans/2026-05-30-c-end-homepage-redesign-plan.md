# C端首页改版实施计划

> **For agentic workers:** 使用 superpowers:executing-plans 逐任务实施。每个步骤用 checkbox (`- [ ]`) 追踪。

**Goal:** 重写 Flutter C端首页，从平淡的列表页升级为高端酒店风格的展示页，包含渐变Banner、欢迎卡片、酒店亮点网格、设施列表和底部信息。

**Architecture:** 单文件重写 `home_page.dart`，拆分为5个区块Widget方法。通过 `AuthBloc` 判断登录状态，通过 `ApiClient` 获取房间信息。未登录用户点击亮点卡片时弹出 `LoginBottomSheet`。

**Tech Stack:** Flutter 3.35+ / flutter_bloc / go_router / dio

---

## 文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `smartstay-flutter/lib/pages/home/home_page.dart` | 重写 | 整体重构首页布局和交互 |

仅涉及 1 个文件。所有任务都在同一个文件中完成。

---

### Task 1: 重写文件头部 + Banner 区块

**Files:**
- Modify: `smartstay-flutter/lib/pages/home/home_page.dart`

- [ ] **Step 1: 替换整个文件内容为新首页框架 + Banner**

将 `home_page.dart` 替换为以下内容。包含 imports、StatefulWidget 骨架、`_buildBanner()` 方法：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../blocs/auth/auth_bloc.dart';
import '../../blocs/auth/auth_state.dart';
import '../../core/api_client.dart';
import '../../widgets/login_bottom_sheet.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  // ── 房间信息状态 ──
  Map<String, dynamic>? _roomInfo;
  bool _roomLoading = false;
  String? _roomError;

  // ── 设施数据 ──
  final _facilities = const [
    {'icon': '🏋️', 'name': '24H健身房', 'time': '营业至24:00', 'price': '免费', 'color': Color(0xFF1677FF)},
    {'icon': '🏊', 'name': '无边泳池', 'time': '水温26°C', 'price': '免费', 'color': Color(0xFF13C2C2)},
    {'icon': '🍽️', 'name': '中西餐厅', 'time': '07:00-22:00', 'price': '收费', 'color': Color(0xFFFA8C16)},
    {'icon': '👕', 'name': '自助洗衣房', 'time': '24小时', 'price': '¥15/次', 'color': Color(0xFF722ED1)},
  ];

  // ── 酒店亮点数据 ──
  final _highlights = const [
    {'icon': '🤖', 'title': 'AI智能管家', 'desc': '一句话送水、报修、调温', 'route': '/ai-chat'},
    {'icon': '🦾', 'title': '机器人送物', 'desc': '自动配送，30分钟送达', 'route': '/work-orders'},
    {'icon': '💡', 'title': '智能客房', 'desc': '手机控灯光·窗帘·空调', 'route': '/room-control'},
    {'icon': '🏊', 'title': '空中花园', 'desc': '泳池+健身房+行政酒廊', 'route': '/facility'},
  ];

  @override
  void initState() {
    super.initState();
    _fetchRoomInfo();
  }

  Future<void> _fetchRoomInfo() async {
    final isLoggedIn = context.read<AuthBloc>().state.status == AuthStatus.authenticated;
    if (!isLoggedIn) return;
    setState(() { _roomLoading = true; _roomError = null; });
    try {
      final resp = await ApiClient().get('/api/rooms/my-room');
      if (mounted) setState(() { _roomInfo = resp.data; _roomLoading = false; });
    } catch (e) {
      if (!mounted) return;
      final msg = e.toString().contains('404') ? '暂无入住房间' : '信息加载失败';
      setState(() { _roomError = msg; _roomLoading = false; });
    }
  }

  Future<void> _callHotel() async {
    final uri = Uri.parse('tel:13800000002');
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _openMap() async {
    final uri = Uri.parse('https://maps.apple.com/?ll=39.9042,116.4074&q=智宿云大酒店');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else {
      final fallback = Uri.parse('geo:39.9042,116.4074?q=智宿云大酒店');
      if (await canLaunchUrl(fallback)) await launchUrl(fallback);
    }
  }

  void _onFeatureTap(String route, {Map<String, dynamic>? extra}) {
    final isLoggedIn = context.read<AuthBloc>().state.status == AuthStatus.authenticated;
    if (!isLoggedIn) {
      LoginBottomSheet.show(context);
      return;
    }
    if (extra != null) {
      context.push(route, extra: extra);
    } else {
      context.go(route);
    }
  }

  String _roomTypeName(String? type) {
    switch (type) {
      case 'big_bed': return '大床房';
      case 'twin': return '双床房';
      case 'suite': return '套房';
      default: return type ?? '';
    }
  }

  String _roomStatusName(String? status) {
    switch (status) {
      case 'occupied': return '已入住';
      case 'vacant': return '空闲';
      default: return status ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoggedIn = context.watch<AuthBloc>().state.status == AuthStatus.authenticated;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      body: ListView(
        children: [
          _buildBanner(),
          if (isLoggedIn) _buildWelcomeCard(),
          _buildSectionTitle('✨ 酒店亮点'),
          _buildHighlightsGrid(),
          _buildSectionTitle('🏢 配套设施'),
          ..._buildFacilityCards(),
          _buildBottomInfo(),
        ],
      ),
    );
  }

  // ── 区块 A：Banner ──
  Widget _buildBanner() {
    return Container(
      height: 200,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1A1A2E), Color(0xFF1677FF)],
        ),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('🏨', style: TextStyle(fontSize: 48)),
            const SizedBox(height: 8),
            const Text('智宿云大酒店',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 4),
            Text('智慧 · 舒适 · 人文',
                style: TextStyle(fontSize: 14, color: Colors.white.withOpacity(0.7))),
            const SizedBox(height: 16),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ElevatedButton.icon(
                  onPressed: _openMap,
                  icon: const Text('🗺️', style: TextStyle(fontSize: 16)),
                  label: const Text('一键导航'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1677FF),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: _callHotel,
                  icon: const Text('📞', style: TextStyle(fontSize: 16)),
                  label: const Text('一键拨号'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF52C41A),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: 验证编译**

```bash
cd smartstay-flutter && dart analyze lib/pages/home/home_page.dart
```

Expected: No issues found (会有未使用方法的 warning，后续 task 会用到)

- [ ] **Step 3: 提交**

```bash
cd smartstay-flutter && git add lib/pages/home/home_page.dart && git commit -m "feat(home): rewrite banner with gradient background"
```

---

### Task 2: 欢迎卡片区块

**Files:**
- Modify: `smartstay-flutter/lib/pages/home/home_page.dart`

- [ ] **Step 1: 添加 `_buildWelcomeCard()` 方法**

在 `_buildBanner()` 方法之后添加：

```dart
  // ── 区块 B：欢迎卡片 ──
  Widget _buildWelcomeCard() {
    final user = context.read<AuthBloc>().state;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 2)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('欢迎回来，${user.name ?? "住客"} 👋',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF333333))),
          const SizedBox(height: 4),
          _buildRoomInfoText(),
          const SizedBox(height: 16),
          _buildQuickActions(),
        ],
      ),
    );
  }

  Widget _buildRoomInfoText() {
    if (_roomLoading) {
      return Container(
        width: 120, height: 14,
        decoration: BoxDecoration(color: Colors.grey[200], borderRadius: BorderRadius.circular(4)),
      );
    }
    if (_roomError != null) {
      return Text(_roomError!, style: const TextStyle(fontSize: 13, color: Color(0xFF999999)));
    }
    if (_roomInfo == null) {
      return const Text('暂无入住房间', style: TextStyle(fontSize: 13, color: Color(0xFF999999)));
    }
    final roomNum = _roomInfo!['room_number'] ?? '';
    final roomType = _roomTypeName(_roomInfo!['room_type']);
    final roomStatus = _roomStatusName(_roomInfo!['status']);
    return Text('房间 $roomNum · $roomType · $roomStatus',
        style: const TextStyle(fontSize: 13, color: Color(0xFF999999)));
  }

  Widget _buildQuickActions() {
    final actions = [
      {'icon': '🤖', 'label': 'AI管家', 'route': '/ai-chat'},
      {'icon': '💡', 'label': '控房', 'route': '/room-control'},
      {'icon': '📋', 'label': '工单', 'route': '/work-orders'},
      {'icon': '📄', 'label': '账单', 'route': '/my'},
    ];
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: actions.map((a) => GestureDetector(
        onTap: () => context.go(a['route'] as String),
        child: Column(
          children: [
            Container(
              width: 56, height: 56,
              decoration: const BoxDecoration(color: Color(0xFFF0F5FF), shape: BoxShape.circle),
              child: Center(child: Text(a['icon'] as String, style: const TextStyle(fontSize: 24))),
            ),
            const SizedBox(height: 6),
            Text(a['label'] as String, style: const TextStyle(fontSize: 11, color: Color(0xFF666666))),
          ],
        ),
      )).toList(),
    );
  }
```

- [ ] **Step 2: 验证编译**

```bash
cd smartstay-flutter && dart analyze lib/pages/home/home_page.dart
```

Expected: No issues found

- [ ] **Step 3: 提交**

```bash
cd smartstay-flutter && git add lib/pages/home/home_page.dart && git commit -m "feat(home): add welcome card with room info and quick actions"
```

---

### Task 3: 酒店亮点网格区块

**Files:**
- Modify: `smartstay-flutter/lib/pages/home/home_page.dart`

- [ ] **Step 1: 添加 `_buildSectionTitle()` 和 `_buildHighlightsGrid()` 方法**

在 `_buildQuickActions()` 方法之后添加：

```dart
  // ── 区块标题 ──
  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFF333333))),
    );
  }

  // ── 区块 C：酒店亮点 ──
  Widget _buildHighlightsGrid() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: GridView.count(
        crossAxisCount: 2,
        childAspectRatio: 1.4,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        children: _highlights.map((h) => _buildHighlightCard(h)).toList(),
      ),
    );
  }

  Widget _buildHighlightCard(Map<String, dynamic> item) {
    return GestureDetector(
      onTap: () {
        if (item['title'] == '空中花园') {
          _onFeatureTap('/facility', extra: {
            'icon': '🏊', 'name': '无边际泳池', 'time': '06:00-23:00',
            'price': '免费', 'dynamic_tip': {'water_temp': '26°C', 'crowd_level': '适中'},
          });
        } else {
          _onFeatureTap(item['route'] as String);
        }
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 2)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(item['icon'] as String, style: const TextStyle(fontSize: 32)),
            const SizedBox(height: 8),
            Text(item['title'] as String,
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: Color(0xFF333333))),
            const SizedBox(height: 2),
            Text(item['desc'] as String,
                style: const TextStyle(fontSize: 12, color: Color(0xFF999999))),
          ],
        ),
      ),
    );
  }
```

- [ ] **Step 2: 验证编译**

```bash
cd smartstay-flutter && dart analyze lib/pages/home/home_page.dart
```

Expected: No issues found

- [ ] **Step 3: 提交**

```bash
cd smartstay-flutter && git add lib/pages/home/home_page.dart && git commit -m "feat(home): add highlight feature cards with login interception"
```

---

### Task 4: 配套设施区块

**Files:**
- Modify: `smartstay-flutter/lib/pages/home/home_page.dart`

- [ ] **Step 1: 添加 `_buildFacilityCards()` 方法**

在 `_buildHighlightCard()` 方法之后添加：

```dart
  // ── 区块 D：配套设施 ──
  List<Widget> _buildFacilityCards() {
    return _facilities.map((f) => Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
      child: GestureDetector(
        onTap: () => context.push('/facility', extra: f),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 1)),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 4, height: 60,
                decoration: BoxDecoration(
                  color: f['color'] as Color,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12), bottomLeft: Radius.circular(12),
                  ),
                ),
              ),
              Expanded(
                child: ListTile(
                  leading: Text(f['icon'] as String, style: const TextStyle(fontSize: 24)),
                  title: Text(f['name'] as String, style: const TextStyle(fontWeight: FontWeight.w500)),
                  subtitle: Text('${f['time']} · ${f['price']}'),
                  trailing: const Icon(Icons.chevron_right, color: Color(0xFFCCCCCC)),
                ),
              ),
            ],
          ),
        ),
      ),
    )).toList();
  }
```

- [ ] **Step 2: 验证编译**

```bash
cd smartstay-flutter && dart analyze lib/pages/home/home_page.dart
```

Expected: No issues found

- [ ] **Step 3: 提交**

```bash
cd smartstay-flutter && git add lib/pages/home/home_page.dart && git commit -m "feat(home): add facility cards with colored left border"
```

---

### Task 5: 底部信息区块 + 整体验证

**Files:**
- Modify: `smartstay-flutter/lib/pages/home/home_page.dart`

- [ ] **Step 1: 添加 `_buildBottomInfo()` 方法**

在 `_buildFacilityCards()` 方法之后添加：

```dart
  // ── 区块 E：底部信息 ──
  Widget _buildBottomInfo() {
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(20),
      color: const Color(0xFFF8F9FA),
      child: Column(
        children: [
          const Text('📍 北京市朝阳区建国路100号',
              style: TextStyle(fontSize: 13, color: Color(0xFF999999))),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _openMap,
                  icon: const Text('🗺️', style: TextStyle(fontSize: 16)),
                  label: const Text('一键导航'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1677FF),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _callHotel,
                  icon: const Text('📞', style: TextStyle(fontSize: 16)),
                  label: const Text('一键拨号'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF52C41A),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
```

- [ ] **Step 2: 完整编译验证**

```bash
cd smartstay-flutter && dart analyze lib/pages/home/home_page.dart
```

Expected: No issues found

- [ ] **Step 3: 全量编译验证（确保无交叉引用问题）**

```bash
cd smartstay-flutter && dart analyze lib/
```

Expected: No issues found

- [ ] **Step 4: 提交**

```bash
cd smartstay-flutter && git add lib/pages/home/home_page.dart && git commit -m "feat(home): add bottom info section and complete homepage redesign"
```

---

### Task 6: harness 更新

**Files:**
- Modify: `feature_list.json`
- Modify: `progress.md`
- Modify: `session-handoff.md`

- [ ] **Step 1: 更新 feature_list.json**

将 F011 添加到 features 数组，状态设为 `done`。

- [ ] **Step 2: 更新 progress.md**

添加 F011 的完成记录。

- [ ] **Step 3: 更新 session-handoff.md**

记录本次会话的变更。

- [ ] **Step 4: 提交**

```bash
cd .. && git add feature_list.json progress.md session-handoff.md && git commit -m "docs: update harness after homepage redesign"
```
