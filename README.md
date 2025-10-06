# 📧 MailMind - AI驱动的智能邮件管理平台

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![AI](https://img.shields.io/badge/AI-GLM--4-00D4AA?style=for-the-badge&logo=openai&logoColor=white)](https://open.bigmodel.cn/)
[![License](https://img.shields.io/badge/License-MIT-FFC107?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v2.0.0-blue?style=for-the-badge)](README.md)

**让AI成为你的邮件管理助手**

一个功能完整的企业级邮件智能管理系统，集成AI摘要、智能分类、多用户管理、异步处理等先进特性

[✨ 功能特色](#-功能特色) • [🚀 快速开始](#-快速开始) • [🏗️ 系统架构](#️-系统架构) • [📚 文档](#-完整文档) • [🤝 贡献](#-贡献指南)

</div>

---

## 📋 目录

- [项目概述](#-项目概述)
- [功能特色](#-功能特色)
- [技术栈](#️-技术栈)
- [系统要求](#-系统要求)
- [快速开始](#-快速开始)
- [系统架构](#-系统架构)
- [核心功能详解](#-核心功能详解)
- [配置说明](#️-配置说明)
- [部署指南](#-部署指南)
- [API文档](#-api文档)
- [故障排除](#-故障排除)
- [性能优化](#-性能优化)
- [完整文档](#-完整文档)
- [更新日志](#-更新日志)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 🎯 项目概述

**MailMind** 是一个基于Flask开发的现代化AI邮件管理平台，专为个人和团队提供智能化的邮件处理解决方案。系统整合了人工智能、异步处理、智能分类等先进技术，显著提升邮件管理效率。

### 核心价值

- **💰 节省时间**: 自动化处理，每天节省30分钟以上
- **📊 提高效率**: AI智能分类，重要邮件不遗漏
- **🎯 精准管理**: 自定义规则，完全个性化
- **🔒 安全可靠**: 多用户隔离，企业级安全
- **🚀 高性能**: 异步处理，支持高并发

### 项目统计

```
📊 代码统计
├── Python代码: 12,000+ 行
├── 前端代码: 8,000+ 行
├── 配置文件: 500+ 行
├── 测试脚本: 2,000+ 行
└── 文档: 50,000+ 行

📁 文件统计  
├── 核心模块: 25个
├── 服务组件: 18个
├── API端点: 60+个
└── 完整文档: 100+份
```

---

## ✨ 功能特色

### 📧 多邮件服务商支持

| 服务商 | 协议 | 认证方式 | 状态 | 特别说明 |
|--------|------|----------|------|----------|
| **Gmail** | IMAP/SMTP | OAuth2 | ⚠️ 需转发 | Google已停止基本认证，建议使用转发功能 |
| **126邮箱** | IMAP/SMTP | 授权码 | ✅ 完全支持 | 推荐使用 |
| **163邮箱** | IMAP/SMTP | 授权码 | ✅ 完全支持 | 推荐使用 |
| **QQ邮箱** | IMAP/SMTP | 授权码 | ✅ 完全支持 | 推荐使用 |
| **新浪邮箱** | IMAP/SMTP | 授权码 | ✅ 完全支持 | 需IMAP ID配置 |
| **Hotmail/Outlook** | IMAP/SMTP | OAuth2 | ⚠️ 需转发 | Microsoft已停用基本认证，建议使用转发功能 |
| **Yahoo** | IMAP/SMTP | 应用密码 | ✅ 完全支持 | - |

**特色功能:**
- 🔄 自动服务商检测
- 🔌 统一连接管理
- ⚙️ IMAP ID命令优化
- 🛡️ 完善的错误处理
- 📝 详细的配置文档
- 📧 邮件转发功能支持（用于Gmail和Outlook）

### 🤖 AI智能功能

#### 🆕 AI邮件助手 (v2.0 重大更新)

**核心特性：**
- 🤖 **智能对话系统** - 自然语言查询邮件
- 🔍 **Function Call技术** - 精准理解意图并执行
- 💬 **多轮对话** - 支持连续对话和上下文理解
- 📊 **智能检索** - 时间、发件人、关键词多维度查询
- 🎯 **快捷命令** - 11个可自定义的快捷操作

**对话示例：**
```
用户: "帮我看下今天的邮件"
AI: 📧 找到了65封今天的邮件，包括3封重要邮件...

用户: "有没有小明发给我的"
AI: 📨 找到5封来自小明的邮件，最近一封是...

用户: "列出最近三天未读的工作邮件"
AI: 💼 找到12封符合条件的邮件...
```

**功能亮点：**
- ✅ 自然语言理解（如"今天"、"近三天"、"重要"）
- ✅ 智能邮件搜索（时间、发件人、分类、关键词）
- ✅ 邮件卡片展示（标题、发件人、摘要、快速操作）
- ✅ 独立窗口查看全部结果
- ✅ 邮件详情查看和回复
- ✅ 对话记录复制/粘贴
- ✅ **聊天记录查看（新功能）** - 在新标签页查看完整聊天历史
- ✅ **导出TXT文件（新功能）** - 一键导出聊天记录为TXT文件，支持持久化保存
- ✅ 本地存储（快捷命令、对话历史）
- ✅ 完整的错误处理和降级机制

**快捷命令（可编辑）：**
| 类型 | 命令示例 |
|------|---------|
| 时间查询 | 今天的邮件、近三天的邮件、本周的邮件 |
| 状态筛选 | 重要邮件、未读邮件 |
| 分类筛选 | 工作邮件、财务邮件 |
| 统计分析 | 本周统计、今天收到多少邮件 |
| 综合检索 | 工作邮件并且重要的、最近三天未读的工作邮件 |

**用户界面：**
- 🎨 悬浮式AI助手按钮
- 💫 流畅的对话界面
- 🎯 实时加载动画
- 📱 响应式设计
- 🌓 深色模式适配
- ✏️ 快捷命令编辑器（添加、删除、修改图标）

---

#### 智能摘要生成
- **AI模型**: 智谱GLM-4 Plus / OpenAI GPT
- **处理方式**: 批量并发处理
- **生成速度**: 1-3秒/封邮件
- **准确率**: 90%+
- **备用机制**: 自动降级策略

#### AI增强特性
- ✅ 根据邮件类型自动分类
- ✅ 重要性智能评分（1-4级）
- ✅ 关键信息提取
- ✅ Markdown渲染支持
- ✅ 多语言支持

### 🗂️ 智能分类系统 (v2.0)

#### 四层分类策略
```
1️⃣ 用户自定义规则 (最高优先级)
   └─ 5种匹配模式 + AND/OR逻辑
   
2️⃣ AI智能分析 (规划中)
   └─ 语义理解 + 上下文分析
   
3️⃣ 关键词规则匹配
   └─ 内置规则库 + 模式识别
   
4️⃣ 默认分类 (兜底机制)
   └─ 确保所有邮件都有分类
```

#### 11种分类类别

| 分类 | 图标 | 颜色 | 说明 |
|------|------|------|------|
| 工作 | 💼 | 蓝色 | 工作相关邮件 |
| 财务 | 💰 | 绿色 | 账单、发票等 |
| 社交 | 👥 | 青色 | 社交平台通知 |
| 购物 | 🛒 | 黄色 | 订单、物流等 |
| 资讯 | 📰 | 灰色 | 新闻、订阅等 |
| 教育 | 🎓 | 蓝色 | 学习相关 |
| 旅行 | ✈️ | 青色 | 旅游、出行 |
| 健康 | 🏥 | 红色 | 医疗健康 |
| 系统 | 🔔 | 黑色 | 系统通知 |
| 垃圾 | 🗑️ | 红色 | 垃圾邮件 |
| 其他 | 📁 | 浅色 | 未分类 |

#### 规则管理功能
- ✅ 拖拽调整优先级
- ✅ 规则导入/导出
- ✅ 实时规则测试
- ✅ 批量应用规则
- ✅ 智能冲突检测
- ✅ 规则效果统计

### 🔄 智能去重系统

**去重策略:**
- **内容哈希**: MD5算法
- **检查范围**: 可配置时间窗口（默认7天）
- **跨账户**: 多邮箱统一去重
- **性能**: O(1)时间复杂度

**去重算法:**
```python
def generate_content_hash(email):
    content = f"{email['subject']}{email['sender']}{email['body']}"
    return hashlib.md5(content.encode()).hexdigest()
```

### 👥 多用户系统

**用户管理:**
- ✅ 用户注册/登录
- ✅ 密码加密存储（SHA-256 + Salt）
- ✅ 会话管理（24小时超时）
- ✅ 管理员权限系统
- ✅ 数据完全隔离

**邮箱账户管理:**
- ✅ 邮箱账户删除（一键彻底删除）
- ✅ 邮箱账户转移（转移给其他用户）
- ✅ 双向通知系统（转移后通知双方）
- ✅ 智能验证（防重复、防自转）
- ✅ 事务保护（确保数据一致性）

**权限控制:**
- 访问控制（所有页面需登录）
- 数据隔离（用户只能看自己的数据）
- 账户绑定（邮箱账户与用户绑定）
- 操作审计（详细日志记录）

### ⚡ 异步处理优化

**核心技术:**
- **Celery**: 分布式任务队列
- **Redis**: 高性能缓存和消息代理
- **线程池**: AI并发处理

**性能提升:**
| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 收取10封邮件 | 15-30秒 | 3-8秒 | **5倍** |
| 收取50封邮件 | 75-150秒 | 15-30秒 | **5倍** |
| 生成AI摘要 | 50-150秒 | 10-30秒 | **5倍** |
| 批量下载附件 | 阻塞 | 后台处理 | **即时响应** |

**用户体验:**
- ✅ 实时进度显示
- ✅ 操作立即响应
- ✅ 后台任务处理
- ✅ 支持高并发

### 🔔 通知系统

**通知类型:**
- 📬 新邮件到达
- ℹ️ 系统信息
- ✅ 操作成功
- ⚠️ 警告提示
- ❌ 错误提醒

**展示方式:**
- 🔔 铃铛徽章（未读数量）
- 📋 下拉面板（最近10条）
- 🎯 Toast通知（即时弹窗）
- 📊 通知中心（完整列表）

**特色功能:**
- 30秒自动更新
- 标记已读/删除
- 筛选和分页
- Redis缓存优化

### 🗑️ 回收站功能

- ✅ 软删除机制（30天保留期）
- ✅ 批量恢复/永久删除
- ✅ 自动清理过期数据
- ✅ 完整的操作历史

### 📄 附件管理

- ✅ 多文件上传支持
- ✅ 批量下载（ZIP打包）
- ✅ 异步文件处理
- ✅ 病毒扫描（规划中）
- ✅ 存储空间管理

### 🔗 转发邮件识别

**识别规则:**
- 主题前缀检测（`Fwd:`、`转发:`）
- 邮件头分析（`X-Forwarded-For`）
- 正文模式匹配

**提取能力:**
- 原始发件人信息
- 转发次数统计
- 完整转发链
- 准确率：95%+

### 🌍 邮件翻译

- ✅ 异步翻译服务
- ✅ 中英互译
- ✅ 翻译缓存优化
- ✅ 标签页展示
- ✅ 数据库持久化

### 🎨 现代化界面

**设计特色:**
- 💫 Bootstrap 5框架
- 🌓 深色模式支持
- 📱 完全响应式设计
- ✨ 优雅的动画效果
- 🎯 直观的数据可视化

**UI组件:**
- 渐变色彩主题
- 卡片式布局
- 加载动画
- 空状态引导
- 操作反馈提示

### 📊 数据统计

- 📈 邮件统计图表
- 📊 分类分布分析
- 👤 发件人排行
- 📅 时间趋势分析
- 🏆 系统性能监控

### 🔧 其他功能

- ✅ 邮件搜索（全文检索）
- ✅ 高级筛选（多维度）
- ✅ 邮件详情查看
- ✅ 快速重新摘要
- ✅ 日志系统（分级记录）
- ✅ 性能监控
- ✅ 数据备份
- ✅ 健康检查端点

---

## 🛠️ 技术栈

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.8+ | 核心语言 |
| **Flask** | 3.0 | Web框架 |
| **SQLite3** | - | 数据存储 |
| **SQLAlchemy** | 2.0+ | ORM |
| **Celery** | 5.3+ | 异步任务 |
| **Redis** | 6.0+ | 缓存/消息队列 |
| **APScheduler** | 3.10+ | 定时任务 |
| **BeautifulSoup4** | 4.12+ | HTML解析 |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Bootstrap** | 5.3 | UI框架 |
| **Font Awesome** | 6.0 | 图标库 |
| **jQuery** | 3.6 | DOM操作 |
| **SortableJS** | 1.15 | 拖拽排序 |
| **Chart.js** | 4.0 | 图表展示 |

### AI服务

| 服务 | 模型 | 用途 |
|------|------|------|
| **智谱AI** | GLM-4 Plus | 邮件摘要 |
| **OpenAI** | GPT-4 | 备用方案 |

### 开发工具

- **Git**: 版本控制
- **Pytest**: 单元测试
- **Pylint**: 代码质量
- **Black**: 代码格式化

---

## 📋 系统要求

### 硬件要求

| 类型 | 最低配置 | 推荐配置 |
|------|----------|----------|
| **CPU** | 2核 | 4核+ |
| **内存** | 2GB | 4GB+ |
| **硬盘** | 1GB | 10GB+ |
| **网络** | 1Mbps | 10Mbps+ |

### 软件要求

- **操作系统**: Windows 10+, Linux, macOS
- **Python**: 3.8或更高版本
- **Redis**: 6.0或更高版本（可选，用于异步处理）
- **浏览器**: Chrome 90+, Firefox 88+, Edge 90+

---

## 🚀 快速开始

### 方式一：标准安装（推荐）

#### 1. 克隆项目
```bash
git clone <repository-url>
cd mailmind
```

#### 2. 创建虚拟环境
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖
```bash
# 核心依赖
pip install -r requirements.txt

# 如需异步处理功能
pip install -r requirements_celery.txt
```

#### 4. 配置环境变量
```bash
# 复制环境变量模板
copy env_example.txt .env  # Windows
cp env_example.txt .env    # Linux/Mac

# 编辑.env文件，配置必要参数
notepad .env  # Windows
nano .env     # Linux/Mac
```

**必需配置项:**
```env
# 应用密钥（必须修改）
SECRET_KEY=your-very-secret-key-change-this-in-production

# AI服务配置（必须配置）
AI_PROVIDER=glm
GLM_API_KEY=your_glm_api_key_here
GLM_MODEL=glm-4-plus

# 系统配置（可选）
CHECK_INTERVAL_MINUTES=30
MAX_EMAILS_PER_RUN=50
SUMMARY_MAX_LENGTH=200
DUPLICATE_CHECK_DAYS=7

# Celery配置（可选，用于异步处理）
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

#### 5. 初始化数据库
```bash
# 数据库会在首次启动时自动创建
# 如需手动初始化
python -c "from models.database import Database; db = Database(); print('数据库初始化完成')"
```

#### 6. 启动应用

**开发模式:**
```bash
python app.py
```

**生产模式（推荐）:**
```bash
# 使用启动脚本
python run_app.py

# 或使用生产服务器
python run_production_windows.py  # Windows
```

#### 7. 访问系统
```
主页: http://localhost:6006
健康检查: http://localhost:6006/health
```

### 方式二：使用批处理脚本（Windows）

#### 快速启动
```bash
# 1. 简单启动（仅Web服务）
start_simple.bat

# 2. 完整启动（Web + Celery）
start_all_完整版.bat

# 3. 调试启动（详细日志）
start_all_debug.bat
```

### 方式三：Docker部署（推荐生产环境）

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 邮件列表  │  │ 分类管理  │  │ 通知中心  │  │ 系统设置  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
┌────────────────────────▼────────────────────────────────────┐
│                      Flask应用层                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│  │ 路由控制   │  │ 认证授权   │  │ 业务逻辑   │  │ 错误处理 │ │
│  └───────────┘  └───────────┘  └───────────┘  └─────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      服务层                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ EmailManager   │  │ Classification │  │ AIClient     │  │
│  │ (邮件管理)      │  │ Service        │  │ (AI服务)     │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ AuthService    │  │ NotificationSvc│  │ Translation  │  │
│  │ (认证服务)      │  │ (通知服务)      │  │ Service      │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   异步任务层 (Celery)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ 邮件处理    │  │ AI摘要生成  │  │ 文件处理    │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      数据层                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ SQLite      │  │ Redis Cache │  │ File System │        │
│  │ (持久化)     │  │ (缓存)       │  │ (文件存储)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
           │                    │                  │
           ▼                    ▼                  ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│ 邮件服务器    │  │ AI服务商          │  │ 外部服务      │
│ IMAP/SMTP    │  │ GLM-4/OpenAI     │  │ (可选)        │
└──────────────┘  └──────────────────┘  └──────────────┘
```

### 核心模块说明

#### 1. 邮件管理器 (EmailManager)
```python
services/email_manager.py
├── fetch_new_emails()      # 获取新邮件
├── parse_email()           # 解析邮件
├── detect_forwarded()      # 转发识别
├── classify_email()        # 邮件分类
└── save_attachments()      # 保存附件
```

#### 2. 分类服务 (ClassificationService)
```python
services/classification_service.py
├── classify_with_rules()   # 规则分类
├── classify_with_ai()      # AI分类
├── classify_with_keywords()# 关键词分类
└── apply_fallback()        # 默认分类
```

#### 3. AI客户端 (AIClient)
```python
services/ai_client.py
├── summarize_email()       # 单封摘要
├── batch_summarize()       # 批量摘要
├── batch_summarize_concurrent() # 并发摘要
└── generate_digest()       # 生成简报
```

#### 4. 认证服务 (AuthService)
```python
services/auth_service.py
├── login()                 # 用户登录
├── register()              # 用户注册
├── get_current_user()      # 获取当前用户
├── require_login()         # 登录装饰器
└── cleanup_sessions()      # 清理会话
```

---

## 💡 核心功能详解

### 邮件收取与处理流程

```
1. 用户触发收取
   ↓
2. 获取用户邮箱账户
   ↓
3. 连接IMAP服务器
   ↓
4. 获取新邮件列表
   ↓
5. 解析邮件内容
   ├── 基本信息（主题、发件人、时间）
   ├── 邮件正文（纯文本 + HTML）
   ├── 附件信息
   └── 转发检测
   ↓
6. 内容去重（MD5哈希）
   ↓
7. 智能分类
   ├── 用户规则匹配
   ├── AI智能分析
   ├── 关键词匹配
   └── 默认分类
   ↓
8. AI摘要生成（并发处理）
   ↓
9. 保存到数据库
   ↓
10. 生成通知
    ↓
11. 更新用户界面
```

### 智能分类算法

```python
def classify_email(email, user_id):
    """四层智能分类算法"""
    
    # 第一层：用户自定义规则
    rule_result = match_user_rules(email, user_id)
    if rule_result.matched:
        return rule_result.category, rule_result.importance
    
    # 第二层：AI智能分析（如果启用）
    if ai_enabled():
        ai_result = ai_classify(email)
        if ai_result.confidence > 0.8:
            return ai_result.category, ai_result.importance
    
    # 第三层：关键词匹配
    keyword_result = match_keywords(email)
    if keyword_result.matched:
        return keyword_result.category, keyword_result.importance
    
    # 第四层：默认分类
    return 'general', 1
```

### 规则匹配引擎

**支持的匹配模式:**

1. **精确匹配 (Exact)**
   ```python
   sender_email == 'boss@company.com'
   ```

2. **包含匹配 (Contains)**
   ```python
   'company' in sender_email
   ```

3. **域名匹配 (Domain)**
   ```python
   sender_email.endswith('@company.com')
   ```

4. **通配符匹配 (Wildcard)**
   ```python
   fnmatch.fnmatch(sender_email, '*@*.edu.cn')
   ```

5. **正则表达式 (Regex)**
   ```python
   re.match(r'^.*-noreply@.*\.com$', sender_email)
   ```

**规则评分系统:**
```python
score = (
    priority_weight * 1.0 +      # 优先级权重
    sender_match * 0.4 +          # 发件人匹配
    subject_match * 0.3 +         # 主题匹配
    body_match * 0.3              # 正文匹配
)
```

---

## ⚙️ 配置说明

### 环境变量配置

创建`.env`文件并配置以下参数：

#### 基础配置
```env
# 应用配置
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
DEBUG=False
PORT=6006

# 数据库配置
DATABASE_PATH=data/emails.db
DUPLICATE_CHECK_DAYS=7
```

#### AI服务配置
```env
# AI提供商选择：glm 或 openai
AI_PROVIDER=glm

# 智谱GLM配置
GLM_API_KEY=your_glm_api_key_here
GLM_MODEL=glm-4-plus
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# OpenAI配置（备用）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1
```

#### 邮件处理配置
```env
# 邮件收取配置
CHECK_INTERVAL_MINUTES=30
MAX_EMAILS_PER_RUN=50
MAX_EMAILS_PER_ACCOUNT=20
DEFAULT_CHECK_DAYS=1

# AI摘要配置
SUMMARY_MAX_LENGTH=200
AI_TIMEOUT=30
AI_MAX_RETRIES=3
```

#### Celery异步配置
```env
# Redis配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# 任务配置
CELERY_TASK_TIME_LIMIT=300
CELERY_WORKER_PREFETCH_MULTIPLIER=1
```

#### 日志配置
```env
# 日志设置
LOG_LEVEL=INFO
LOG_FILE=logs/email_digest.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

### 邮箱配置指南

#### Gmail配置

**⚠️ 重要提示：** Google已于2024年停止支持传统客户端的基本身份验证（用户名+密码），目前仅支持OAuth2授权方式。

**推荐方案：使用邮件转发功能**

1. **登录Gmail**
   - 访问：https://mail.google.com/
   - 进入设置 → 转发和POP/IMAP

2. **设置邮件转发**
   - 添加转发地址（推荐使用126或163邮箱）
   - 选择"转发副本"或"转发并保留Gmail的副本"
   - 确认转发设置

3. **在本系统中配置接收邮箱**
   ```
   邮箱: 您的126/163邮箱
   密码: 使用授权码
   服务商: 126/163 (自动检测)
   ```

#### 126/163邮箱配置

1. **开启IMAP/SMTP服务**
   - 登录网易邮箱
   - 设置 → POP3/SMTP/IMAP
   - 开启服务

2. **获取授权码**
   - 点击"开启服务"
   - 通过手机验证
   - 记录授权码

3. **在系统中配置**
   ```
   邮箱: your-email@126.com 或 @163.com
   密码: 使用授权码（不是登录密码）
   服务商: 126/163 (自动检测)
   ```

#### QQ邮箱配置

1. **开启服务**
   - 登录QQ邮箱
   - 设置 → 账户
   - 开启IMAP/SMTP服务

2. **获取授权码**
   - 通过密保手机验证
   - 记录16位授权码

3. **在系统中配置**
   ```
   邮箱: your-email@qq.com
   密码: 使用授权码
   服务商: QQ (自动检测)
   ```

#### 新浪邮箱配置

**特殊说明**: 新浪邮箱需要特殊配置

1. **获取授权码**
   - 登录新浪邮箱
   - 设置 → 客户端POP/IMAP/SMTP服务
   - 开启服务并获取授权码

2. **配置IMAP ID**
   ```python
   # 系统已自动配置
   IMAP_ID = {
       'name': 'sina.com',
       'version': '1.0.0',
       'vendor': 'sina'
   }
   ```

#### Hotmail/Outlook配置

**⚠️ 重要提示：** Microsoft已于2022年10月起逐步停用基本身份验证，目前仅支持OAuth2等现代身份验证方式。

**推荐方案：使用邮件转发功能**

1. **登录Outlook**
   - 访问：https://outlook.live.com/
   - 进入设置 → 邮件 → 转发

2. **设置邮件转发**
   - 启用转发功能
   - 添加转发地址（推荐使用126或163邮箱）
   - 选择是否保留副本
   - 保存设置

3. **在本系统中配置接收邮箱**
   ```
   邮箱: 您的126/163邮箱
   密码: 使用授权码
   服务商: 126/163 (自动检测)
   ```

---

## 🚀 部署指南

### Linux环境部署

#### 1. 使用Gunicorn（推荐）

```bash
# 安装Gunicorn
pip install gunicorn

# 启动应用
gunicorn -w 4 -b 0.0.0.0:6006 app:app

# 后台运行
nohup gunicorn -w 4 -b 0.0.0.0:6006 app:app > gunicorn.log 2>&1 &

# 使用配置文件
gunicorn -c gunicorn.conf.py app:app
```

**gunicorn.conf.py示例:**
```python
bind = "0.0.0.0:6006"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
```

#### 2. 使用Systemd管理

创建服务文件 `/etc/systemd/system/email-digest.service`:

```ini
[Unit]
Description=AI Email Digest Service
After=network.target redis.service

[Service]
Type=notify
User=your-username
WorkingDirectory=/path/to/fecth_email_with_ai
Environment=PATH=/path/to/fecth_email_with_ai/venv/bin
ExecStart=/path/to/fecth_email_with_ai/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=always
RestartSec=10
StandardOutput=append:/var/log/email-digest/app.log
StandardError=append:/var/log/email-digest/error.log

[Install]
WantedBy=multi-user.target
```

**管理服务:**
```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start email-digest

# 开机自启
sudo systemctl enable email-digest

# 查看状态
sudo systemctl status email-digest

# 查看日志
sudo journalctl -u email-digest -f
```

### Windows环境部署

#### 1. 使用Waitress

**注意**: Gunicorn不支持Windows，推荐使用Waitress

```bash
# 安装Waitress
pip install waitress

# 方式1：使用启动脚本（推荐）
python run_production_windows.py

# 方式2：直接运行
python -c "from waitress import serve; from app import app; serve(app, host='0.0.0.0', port=6006, threads=8)"
```

#### 2. 使用NSSM作为Windows服务

```bash
# 1. 下载NSSM
# https://nssm.cc/download

# 2. 安装服务
nssm install EmailDigestService "python.exe" "D:\path\to\project\run_production_windows.py"

# 3. 配置服务
nssm set EmailDigestService AppDirectory "D:\path\to\project"
nssm set EmailDigestService AppStdout "D:\path\to\project\logs\service.log"
nssm set EmailDigestService AppStderr "D:\path\to\project\logs\service_error.log"

# 4. 启动服务
nssm start EmailDigestService

# 5. 查看状态
nssm status EmailDigestService
```

### Nginx反向代理

创建配置文件 `/etc/nginx/sites-available/email-digest`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # SSL配置（推荐生产环境）
    # listen 443 ssl http2;
    # ssl_certificate /path/to/cert.pem;
    # ssl_certificate_key /path/to/key.pem;
    
    # 日志
    access_log /var/log/nginx/email-digest-access.log;
    error_log /var/log/nginx/email-digest-error.log;
    
    # 反向代理
    location / {
        proxy_pass http://127.0.0.1:6006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 静态文件
    location /static {
        alias /path/to/fecth_email_with_ai/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # 上传限制
    client_max_body_size 50M;
    
    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

**启用配置:**
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/email-digest /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载Nginx
sudo systemctl reload nginx
```

### Docker部署

#### 1. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p data logs

# 暴露端口
EXPOSE 6006

# 启动命令
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
```

#### 2. docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "6006:6006"
    environment:
      - FLASK_ENV=production
      - DATABASE_PATH=/app/data/emails.db
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./email_attachments:/app/email_attachments
    depends_on:
      - redis
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  celery:
    build: .
    command: celery -A services.celery_app worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis_data:
```

**部署命令:**
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

### Celery Worker部署

#### Linux（使用Systemd）

创建 `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker Service
After=network.target redis.service

[Service]
Type=forking
User=your-username
WorkingDirectory=/path/to/fecth_email_with_ai
Environment=PATH=/path/to/fecth_email_with_ai/venv/bin
ExecStart=/path/to/fecth_email_with_ai/venv/bin/celery -A services.celery_app worker --loglevel=info --pidfile=/var/run/celery/worker.pid --logfile=/var/log/celery/worker.log --detach
ExecStop=/path/to/fecth_email_with_ai/venv/bin/celery -A services.celery_app control shutdown
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Windows（使用批处理脚本）

创建 `start_celery_worker.bat`:

```batch
@echo off
cd /d %~dp0
call venv\Scripts\activate
celery -A services.celery_app worker --loglevel=info --pool=solo
```

**或使用NSSM:**
```bash
nssm install CeleryWorker "celery.exe" "-A services.celery_app worker --loglevel=info --pool=solo"
nssm set CeleryWorker AppDirectory "D:\path\to\project"
nssm start CeleryWorker
```

---

## 📡 API文档

### 认证相关

#### POST /api/v1/auth/register
**注册新用户**

**请求体:**
```json
{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe"
}
```

**响应:**
```json
{
    "success": true,
    "message": "注册成功",
    "user_id": 1
}
```

#### POST /api/v1/auth/login
**用户登录**

**请求体:**
```json
{
    "username": "johndoe",
    "password": "SecurePass123"
}
```

**响应:**
```json
{
    "success": true,
    "message": "登录成功",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com"
    },
    "session_token": "abc123..."
}
```

### 邮件相关

#### GET /api/v1/emails
**获取邮件列表**

**查询参数:**
- `page`: 页码（默认1）
- `per_page`: 每页数量（默认20）
- `category`: 分类筛选
- `provider`: 服务商筛选
- `search`: 搜索关键词

**响应:**
```json
{
    "emails": [...],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "pages": 5
    }
}
```

#### POST /trigger
**手动触发邮件收取**

**响应:**
```json
{
    "success": true,
    "message": "邮件处理已启动",
    "task_id": "task-uuid-123"
}
```

#### GET /api/task-status/<task_id>
**查询任务状态**

**响应:**
```json
{
    "state": "PROGRESS",
    "current": 50,
    "total": 100,
    "status": "正在生成AI摘要..."
}
```

### 分类规则相关

#### GET /api/v1/classification/rules
**获取规则列表**

**响应:**
```json
{
    "rules": [
        {
            "id": 1,
            "rule_name": "工作邮件",
            "category": "work",
            "importance": 2,
            "sender_pattern": "@company.com",
            "is_active": true
        }
    ]
}
```

#### POST /api/v1/classification/rules
**创建新规则**

**请求体:**
```json
{
    "rule_name": "重要客户",
    "category": "work",
    "importance": 3,
    "sender_pattern": "vip@example.com",
    "sender_match_type": "exact",
    "subject_keywords": ["urgent", "important"],
    "subject_logic": "or"
}
```

#### POST /api/v1/classification/rules/<rule_id>/apply
**应用规则到现有邮件**

**响应:**
```json
{
    "success": true,
    "updated_count": 25,
    "message": "规则已应用到25封邮件"
}
```

### 通知相关

#### GET /api/notifications
**获取通知列表**

**查询参数:**
- `page`: 页码
- `per_page`: 每页数量
- `type`: 通知类型筛选
- `is_read`: 是否已读

**响应:**
```json
{
    "notifications": [
        {
            "id": 1,
            "type": "success",
            "title": "新邮件到达",
            "message": "成功收取3封新邮件",
            "is_read": false,
            "created_at": "2025-10-04 10:30:00"
        }
    ],
    "unread_count": 5
}
```

#### POST /api/notifications/<id>/read
**标记通知为已读**

**响应:**
```json
{
    "success": true,
    "message": "已标记为已读"
}
```

**完整API文档:** 请查看 [API详细文档](docs/API_DOCUMENTATION.md)

---

## 🔍 故障排除

### 常见问题

#### 1. 邮箱连接失败

**症状:**
```
Error: Login failed for account xxx@xxx.com
```

**可能原因:**
- ❌ 使用了登录密码而非授权码
- ❌ IMAP/SMTP服务未开启
- ❌ 授权码输入错误
- ❌ 网络连接问题

**解决方案:**
```bash
# 1. 检查邮箱配置
- 确认已获取正确的授权码
- 确认IMAP/SMTP服务已开启

# 2. 测试连接
python test_scripts/test_email_connection.py

# 3. 查看详细日志
tail -f logs/email_digest.log | grep "连接"
```

#### 2. AI摘要生成失败

**症状:**
```
Error: AI summary generation failed
```

**可能原因:**
- ❌ API密钥未配置或无效
- ❌ API配额用完
- ❌ 网络无法访问API
- ❌ 邮件内容格式问题

**解决方案:**
```bash
# 1. 检查API密钥
echo $GLM_API_KEY

# 2. 测试API连接
python test_scripts/test_ai_service.py

# 3. 查看API日志
tail -f logs/email_digest.log | grep "AI"

# 4. 检查备用摘要机制
# 系统会自动降级使用基础摘要
```

#### 3. Celery Worker无法启动

**症状:**
```
Error: Cannot connect to redis://localhost:6379
```

**可能原因:**
- ❌ Redis服务未启动
- ❌ Redis连接配置错误
- ❌ 端口被占用

**解决方案:**
```bash
# 1. 检查Redis服务
# Windows:
tasklist | findstr redis

# Linux:
systemctl status redis

# 2. 测试Redis连接
redis-cli ping

# 3. 检查端口
netstat -an | findstr 6379

# 4. 启动Redis
# Windows:
redis-server.exe

# Linux:
sudo systemctl start redis
```

#### 4. 数据库错误

**症状:**
```
Error: database is locked
```

**可能原因:**
- ❌ 多个进程同时访问数据库
- ❌ 数据库文件权限问题
- ❌ 磁盘空间不足

**解决方案:**
```bash
# 1. 检查数据库文件
ls -la data/emails.db

# 2. 检查磁盘空间
df -h

# 3. 重建数据库索引
python -c "from models.database import Database; db = Database(); db.vacuum()"

# 4. 备份并重建
cp data/emails.db data/emails_backup.db
python -c "from models.database import Database; Database()"
```

#### 5. 定时任务不执行

**症状:**
定时任务没有自动执行

**可能原因:**
- ❌ APScheduler未正常启动
- ❌ 系统时间不正确
- ❌ 任务配置错误

**解决方案:**
```bash
# 1. 检查日志
tail -f logs/email_digest.log | grep "scheduler"

# 2. 验证系统时间
date

# 3. 手动触发测试
curl -X POST http://localhost:6006/trigger

# 4. 检查定时任务配置
python -c "from app import scheduler; print(scheduler.get_jobs())"
```

### 日志查看

#### 应用日志
```bash
# 实时查看
tail -f logs/email_digest.log

# 查看错误
grep "ERROR" logs/email_digest.log

# 查看最近100行
tail -n 100 logs/email_digest.log

# 按日期筛选
grep "2025-10-04" logs/email_digest.log
```

#### Celery日志
```bash
# Windows
type logs\celery_*.log

# Linux
tail -f logs/celery_*.log
```

#### 系统服务日志
```bash
# Systemd服务日志
journalctl -u email-digest -f

# Docker容器日志
docker-compose logs -f web
docker-compose logs -f celery
```

### 性能调优

#### 数据库优化
```bash
# 重建索引
python -c "from models.database import Database; db = Database(); db.reindex()"

# 清理旧数据
python -c "from models.database import Database; db = Database(); db.cleanup_old_emails(days=90)"

# 数据库真空
python -c "from models.database import Database; db = Database(); db.vacuum()"
```

#### 缓存清理
```bash
# 清理Redis缓存
redis-cli FLUSHDB

# 清理Python缓存
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

---

## 📊 性能优化

### 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 邮件收取速度 | <5秒/10封 | 并发处理 |
| AI摘要生成 | <3秒/封 | 单封邮件 |
| 页面加载时间 | <2秒 | 首次加载 |
| API响应时间 | <200ms | 普通请求 |
| 数据库查询 | <100ms | 单次查询 |
| 内存占用 | <500MB | 正常运行 |
| CPU使用率 | <30% | 平均负载 |

### 优化建议

#### 1. 数据库优化

**索引优化:**
```sql
-- 邮件表索引
CREATE INDEX IF NOT EXISTS idx_emails_user_id ON emails(user_id);
CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_category ON emails(category);
CREATE INDEX IF NOT EXISTS idx_emails_content_hash ON emails(content_hash);

-- 分类规则表索引
CREATE INDEX IF NOT EXISTS idx_rules_user_id ON classification_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_rules_priority ON classification_rules(priority DESC);
```

**定期清理:**
```python
# 清理90天前的已删除邮件
db.cleanup_old_deleted_emails(days=90)

# 清理30天前的通知
db.clear_old_notifications(days=30)

# 清理过期会话
db.cleanup_expired_sessions()
```

#### 2. 缓存策略

**Redis缓存配置:**
```python
# 缓存用户信息（1小时）
cache.set(f'user:{user_id}', user_data, ex=3600)

# 缓存邮件列表（5分钟）
cache.set(f'emails:{user_id}:page:{page}', emails, ex=300)

# 缓存AI分析结果（24小时）
cache.set(f'ai_summary:{email_id}', summary, ex=86400)
```

#### 3. 异步处理

**批量操作异步化:**
```python
# 批量AI摘要（并发处理）
tasks = [generate_summary_async.delay(email) for email in emails]
results = [task.get(timeout=30) for task in tasks]

# 批量文件处理（后台任务）
process_attachments_async.delay(attachment_list)
```

#### 4. 前端优化

**资源优化:**
- 使用CDN加速静态资源
- 启用Gzip压缩
- 图片懒加载
- 代码分割和按需加载

**缓存策略:**
```javascript
// Service Worker缓存
// 缓存静态资源
cache.addAll([
    '/static/css/style.css',
    '/static/js/main.js'
]);
```

#### 5. 监控和告警

**性能监控工具:**
```bash
# 安装Flower监控Celery
pip install flower
celery -A services.celery_app flower --port=5555

# 访问监控面板
http://localhost:5555
```

**日志分析:**
```bash
# 统计错误数量
grep "ERROR" logs/email_digest.log | wc -l

# 分析慢查询
grep "slow query" logs/email_digest.log

# 监控内存使用
ps aux | grep python
```

---

## 📚 完整文档

### 开发文档（100+份）

#### 核心功能文档
- [项目概览](docs/PROJECT_OVERVIEW.md) - 系统整体架构和功能
- [快速启动](docs/QUICK_START.md) - 5分钟快速上手
- [部署指南](docs/DEPLOYMENT_COMPLETE.md) - 完整部署说明

#### 用户系统文档
- [用户系统指南](docs/USER_SYSTEM_GUIDE.md) - 多用户功能说明
- [用户隔离实现](docs/USER_ISOLATION_COMPLETE.md) - 数据隔离机制

#### 分类系统文档
- [分类功能概述](docs/CLASSIFICATION_QUICK_START.md) - 快速入门
- [分类用户手册](docs/USER_MANUAL_CLASSIFICATION.md) - 详细使用说明
- [分类项目回顾](docs/CLASSIFICATION_PROJECT_REVIEW_AND_NEXT_STEPS.md) - 完整技术方案
- [UI改进文档](docs/CLASSIFICATION_UI_IMPROVEMENT.md) - 界面优化说明

#### 异步优化文档
- [异步优化方案](docs/异步优化方案.md) - 完整优化策略
- [Celery配置说明](docs/Celery日志配置说明.md) - 任务队列配置
- [定时任务说明](docs/定时任务与Celery关系说明.md) - 定时任务机制

#### 通知系统文档
- [通知系统总结](docs/NOTIFICATION_SYSTEM_FINAL_SUMMARY.md) - 完整实现文档
- [前端集成文档](docs/FRONTEND_NOTIFICATION_INTEGRATION_COMPLETE.md) - 前端对接说明
- [快速参考](docs/QUICK_START_NOTIFICATION.md) - 使用指南

#### 邮箱配置文档
- [126邮箱配置](docs/126邮箱_Unsafe_Login_官方解决方案.md) - 详细配置步骤
- [163邮箱优化](docs/163邮箱优化完成总结.md) - 优化说明
- [新浪邮箱配置](docs/新浪邮箱配置指南.md) - 特殊配置说明
- [IMAP ID修复](docs/IMAP_ID命令修复总结.md) - 连接优化
- [邮件账户管理](docs/邮件账户功能增强总结.md) - 删除和转移功能
- [账户管理详解](docs/邮件账户删除和转移功能说明.md) - 完整使用指南

#### 特色功能文档
- [转发邮件识别](docs/转发邮件功能_README.md) - 转发检测功能
- [附件管理](docs/ATTACHMENT_FEATURE_COMPLETE.md) - 附件处理说明
- [回收站功能](docs/RECYCLE_BIN_FEATURE.md) - 回收站使用
- [翻译功能](docs/EMAIL_TRANSLATION_DATABASE_STORAGE_COMPLETE.md) - 邮件翻译

#### 问题修复文档
- [时区问题修复](docs/修复总结_时区和去重问题.md) - 时区处理
- [去重问题修复](docs/邮件去重问题分析与修复.md) - 去重优化
- [简报显示修复](docs/简报显示问题修复总结.md) - 显示问题解决

#### 测试文档
- [测试指南](docs/FINAL_TEST_GUIDE.md) - 完整测试方案
- [交付清单](docs/DELIVERY_CHECKLIST.md) - 功能验收清单

### 启动文档

- [启动说明](启动文件说明.txt) - 各启动方式说明
- [启动成功](启动成功说明.txt) - 成功启动标志
- [问题诊断](启动问题诊断指南.txt) - 常见启动问题
- [快速指南](快速启动指南.txt) - 快速启动步骤

---

## 📝 更新日志

### v2.0.1 (2025-10-06) - 最新版本 🎉

**🆕 AI邮件助手 - 聊天记录查看与导出功能**

**新增功能：**
- 📜 **聊天记录查看** - 在新标签页查看完整聊天历史
  - 精美的渐变紫色主题界面
  - 统计信息展示（总消息数、用户消息、AI回复）
  - 支持复制单条消息或全部记录
  - 包含相关邮件信息展示
  - 全选功能和选择高亮效果
  - 响应式设计，完美支持各种屏幕

- 💾 **导出为TXT文件** - 持久化保存聊天记录
  - 一键导出完整聊天记录为TXT文本文件
  - 文件名自动包含日期时间戳（如：AI邮件助手聊天记录_2025-10-06_15-30-45.txt）
  - 格式化文本输出，包含完整消息和邮件信息
  - 支持用户自定义存储位置
  - UTF-8编码，支持中文显示

**功能特色：**
- 🎨 **精美UI设计** - 渐变背景、卡片式布局、悬停效果
- 📊 **详细统计** - 消息数量、角色分布、导出时间
- 📋 **灵活复制** - 支持单条或全部复制到剪贴板
- 💾 **持久化导出** - TXT文件导出，永久保存聊天记录
- 🔍 **完整信息** - 显示消息时间、角色、内容和相关邮件
- ✨ **用户友好** - Toast提示、视觉反馈、错误处理

**技术实现：**
- 从前端AI助手窗口提取聊天记录
- 动态生成完整HTML页面
- 独立新标签页展示，不影响当前会话
- 使用剪贴板API支持一键复制
- 使用Blob API实现文件下载
- 自动生成带时间戳的文件名
- 完整的错误处理和降级机制

---

### v2.0.0 (2025-10-06)

**🆕 AI邮件助手 - 重大功能更新**

**核心功能：**
- 🤖 **智能对话系统** - 全新的AI邮件助手，支持自然语言查询
- 🔍 **Function Call技术** - 基于GLM-4 Function Call的精准意图识别
- 💬 **多轮对话支持** - 智能上下文理解，支持连续对话
- 📊 **智能邮件检索** - 时间、发件人、分类、关键词多维度查询
- 🎯 **快捷命令系统** - 11个默认命令，支持完全自定义

**用户体验优化：**
- ✨ 悬浮式AI助手入口
- ✨ 流畅的对话界面
- ✨ 邮件卡片展示（带快速操作）
- ✨ 独立窗口查看全部结果（两行紧凑布局）
- ✨ 完整的邮件详情查看和回复
- ✨ 对话记录复制/粘贴功能
- ✨ 快捷命令编辑器（图标选择器、拖拽排序）
- ✨ Toast通知系统
- ✨ LocalStorage持久化存储

**技术特性：**
- 🔧 Function Call自动降级机制
- 🔧 智能邮件缓存
- 🔧 多轮对话上下文管理
- 🔧 详细的调试日志系统
- 🔧 完善的错误处理

**AI助手文档（50+份）：**
- 📚 [AI助手模态框优化](docs/AI助手模态框优化-快捷命令编辑.md)
- 📚 [邮件检索窗口功能](docs/AI助手邮件检索窗口功能完善.md)
- 📚 [多轮对话修复](docs/AI助手多轮对话修复说明.md)
- 📚 [智能邮件缓存](docs/AI助手智能邮件缓存功能说明.md)
- 📚 [功能开发总结](docs/功能开发总结_2025-10-06.md)
- 📚 [技术分析与改进](docs/AI助手技术分析与改进方案.md)
- 📚 还有40+份详细技术文档...

**邮件交互增强：**
- ✨ 独立窗口邮件详情查看
- ✨ 新标签页打开回复
- ✨ 紧凑两行邮件卡片布局
- ✨ 智能日期格式化
- ✨ 完整的HTML/纯文本邮件支持

---

### v1.1.0 (2025-10-04)

**重大更新:**
- ✨ 邮箱账户管理增强
  - 邮箱账户删除功能
  - 邮箱账户转移功能
  - 双向通知系统
- ✨ 邮件服务商支持更新
  - Gmail/Outlook OAuth2说明
  - 邮件转发功能指引
  - 配置文档优化

**功能增强:**
- ✨ 智能验证机制（防重复、防自转）
- ✨ 事务保护（确保数据一致性）
- ✨ 完整的错误处理和日志记录
- ✨ 友好的用户界面提示

**文档更新:**
- 📚 新增《邮件账户功能增强总结》
- 📚 新增《邮件账户删除和转移功能说明》
- 📚 更新邮箱配置指南

### v1.9.0 (2025-10-03)

**重大更新:**
- ✨ 智能分类系统v2.0
  - 四层分类策略
  - 11种分类类别
  - 5种匹配模式
  - 拖拽排序功能
  
**功能增强:**
- ✨ 转发邮件识别功能
- ✨ 邮件翻译功能
- ✨ 回收站功能
- ✨ 附件批量下载优化

**性能优化:**
- ⚡ 异步处理优化（性能提升5倍）
- ⚡ AI并发处理
- ⚡ 数据库索引优化

### v1.5.0 (2025-10-02)

**新增功能:**
- ✨ 多用户系统
- ✨ 用户认证和权限控制
- ✨ 数据隔离
- ✨ 管理员功能

**修复问题:**
- 🐛 时区显示问题
- 🐛 邮件去重问题
- 🐛 简报重复邮件

### v1.0.0 (2025-09-30) - 首次发布

**核心功能:**
- ✨ 多邮件服务商支持
- ✨ AI智能摘要
- ✨ 邮件分类
- ✨ 定时任务
- ✨ 现代化界面

---

## 🤝 贡献指南

### 如何贡献

我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告Bug
- 💡 提出新功能建议
- 📖 改进文档
- 🔧 提交代码修复
- ✨ 开发新功能

### 贡献流程

1. **Fork项目**
   ```bash
   # Fork到自己的GitHub账号
   # 克隆到本地
   git clone https://github.com/wyg5208/mailmind.git
   ```

2. **创建特性分支**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **提交更改**
   ```bash
   git add .
   git commit -m "Add: amazing new feature"
   ```

4. **推送分支**
   ```bash
   git push origin feature/amazing-feature
   ```

5. **创建Pull Request**
   - 访问GitHub仓库
   - 点击"New Pull Request"
   - 填写详细的PR说明

### 代码规范

**Python代码规范:**
```bash
# 使用Black格式化
black .

# 使用Pylint检查
pylint services/ models/ routes/

# 类型提示
from typing import List, Dict, Optional
```

**提交信息规范:**
```
类型: 简短描述

详细描述（可选）

类型包括:
- Add: 新增功能
- Fix: 修复Bug
- Update: 更新功能
- Docs: 文档更新
- Style: 代码格式
- Refactor: 重构
- Test: 测试相关
- Chore: 构建/工具
```

### 开发环境设置

```bash
# 1. 安装开发依赖
pip install -r requirements_dev.txt

# 2. 配置pre-commit
pre-commit install

# 3. 运行测试
pytest tests/

# 4. 检查代码质量
pylint services/
black --check .
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

```
MIT License

Copyright (c) 2025 MailMind Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 💬 支持与反馈

### 获取帮助

如果您在使用过程中遇到问题或有建议，请：

1. **查看文档** - 先查阅本文档和其他相关文档
2. **搜索Issues** - 搜索是否已有类似问题
3. **创建Issue** - 创建新的Issue描述问题
4. **联系维护者** - 通过邮件或其他方式联系

### 问题反馈

**创建Issue时请提供:**
- 系统环境（操作系统、Python版本）
- 完整的错误信息
- 复现步骤
- 相关日志

### 功能建议

**提出功能建议时请说明:**
- 功能的使用场景
- 预期效果
- 可能的实现方案
- 对现有功能的影响

---

## 🌟 致谢

感谢所有为本项目做出贡献的开发者和用户！

特别感谢以下开源项目：

- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Celery](https://docs.celeryq.dev/) - 异步任务队列
- [Bootstrap](https://getbootstrap.com/) - UI框架
- [智谱AI](https://open.bigmodel.cn/) - AI服务
- [OpenAI](https://openai.com/) - AI服务

---

## 📞 联系方式

- **项目主页**: [GitHub Repository]
- **文档站点**: [Documentation Site]
- **问题反馈**: [GitHub Issues]
- **讨论区**: [GitHub Discussions]

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给它一个Star！**

Made with ❤️ by MailMind Team

[⬆ 回到顶部](#-mailmind---ai驱动的智能邮件管理平台)

</div>

---

**最后更新**: 2025-10-06  
**文档版本**: v2.0.1  
**项目版本**: v2.0.0  
**项目状态**: 🚀 生产就绪

**让 AI 成为你的邮件管理助手！** 🎉

## 🆕 最新功能亮点 (v2.0.0) - AI邮件助手

### 🤖 AI邮件助手 - 革命性的邮件交互方式

系统全新推出**AI邮件助手**，通过自然语言对话即可完成邮件查询、管理等操作：

**1. 智能对话系统** 💬
```
只需说：
- "帮我看下今天的邮件"
- "有没有小明发给我的邮件"  
- "列出最近三天未读的工作邮件"
- "本周收到多少封重要邮件"

AI助手立即理解并执行！
```

**2. Function Call技术** 🔍
- 基于GLM-4 Function Call的精准意图识别
- 自动提取时间、发件人、分类等查询条件
- 智能降级机制，确保100%响应
- 详细的执行日志追踪

**3. 多轮对话支持** 🔄
- 智能上下文理解
- 记忆之前的对话内容
- 支持连续追问和补充查询
- 对话历史持久化存储

**4. 快捷命令系统** ⚡
- **11个默认命令**：今天的邮件、重要邮件、工作邮件等
- **完全可自定义**：添加、删除、修改文字和图标
- **智能分类**：时间、状态、分类、统计、综合查询
- **本地存储**：配置永久保存

**5. 快捷命令编辑器** ✏️
- 可视化编辑界面
- 20个图标可选
- 一键恢复默认
- 拖拽调整顺序（计划中）

**6. 独立窗口查看** 🪟
- 紧凑两行邮件卡片布局
- 独立窗口显示全部结果
- 完整的邮件详情模态框
- 新标签页打开回复

**7. 用户体验优化** ✨
- 悬浮式AI助手按钮
- 流畅的对话动画
- Toast通知系统
- 对话记录复制/粘贴
- 深色模式适配

**使用场景:**
- 快速查询今天/本周的邮件
- 查找特定发件人的邮件
- 筛选未读的重要工作邮件
- 统计邮件数量和分布
- 多条件组合查询

**技术亮点:**
- 🔧 Function Call自动降级
- 🔧 智能邮件缓存
- 🔧 多轮对话上下文
- 🔧 详细调试日志
- 🔧 完善错误处理

**详细文档（50+份）:**
- [快捷命令编辑](docs/AI助手模态框优化-快捷命令编辑.md)
- [邮件检索窗口](docs/AI助手邮件检索窗口功能完善.md)
- [多轮对话修复](docs/AI助手多轮对话修复说明.md)
- [智能邮件缓存](docs/AI助手智能邮件缓存功能说明.md)
- [功能开发总结](docs/功能开发总结_2025-10-06.md)
- [技术分析改进](docs/AI助手技术分析与改进方案.md)
- 查看`docs/`目录获取完整文档列表

**体验AI助手:**
1. 启动系统后，点击右下角的🤖图标
2. 说出您的需求，如"今天的邮件"
3. AI立即为您检索并展示结果
4. 点击"编辑"图标自定义快捷命令

---

### 📮 Gmail和Outlook用户重要提示

由于Google和Microsoft已停止支持基本身份验证，我们建议Gmail和Outlook用户：

1. **使用邮件转发** - 将邮件转发到126/163等支持的邮箱
2. **查看配置指南** - README中有详细的转发设置步骤
3. **推荐使用126/163** - 这些邮箱完全支持且配置简单

详见：[邮箱配置指南](#邮箱配置指南)
