/**
 * AI助手前端脚本
 * 提供悬浮对话窗口、消息处理、邮件展示等功能
 */

class AIAssistant {
    constructor() {
        this.isOpen = false;
        this.isMinimized = false;
        this.isFullscreen = false;
        this.messages = [];
        this.context = {
            selected_email_ids: [],
            conversation_history: []
        };
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        
        // 邮件缓存：用于多轮对话中保持邮件显示
        this.lastEmails = [];
        this.lastEmailSearchQuery = '';
        
        this.init();
    }
    
    init() {
        // 创建DOM元素
        this.createElements();
        
        // 绑定事件
        this.bindEvents();
        
        // 检查存储使用量
        this.checkStorageUsage();
        
        // 加载对话历史
        this.loadHistory();
        
        // 显示欢迎消息
        this.showWelcome();
    }
    
    createElements() {
        // 创建悬浮触发按钮
        const trigger = document.createElement('button');
        trigger.id = 'ai-assistant-trigger';
        trigger.innerHTML = '<i class="fas fa-robot"></i><span class="badge"></span>';
        trigger.title = 'AI助手';
        document.body.appendChild(trigger);
        
        // 创建对话窗口
        const panel = document.createElement('div');
        panel.id = 'ai-assistant-panel';
        panel.innerHTML = `
            <div class="ai-panel-header">
                <div class="ai-panel-title">
                    <i class="fas fa-robot"></i>
                    <span>AI邮件助手</span>
                </div>
                <div class="ai-panel-actions">
                    <button id="ai-panel-fullscreen" title="全屏">
                        <i class="fas fa-expand"></i>
                    </button>
                    <button id="ai-panel-minimize" title="最小化">
                        <i class="fas fa-minus"></i>
                    </button>
                    <button id="ai-panel-close" title="关闭">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="ai-welcome-header">
                <h4>👋 你好！我是AI邮件助手</h4>
                <p>我可以帮您快速查找和管理邮件，试试以下快捷命令：</p>
            </div>
            <div class="ai-quick-commands" id="ai-quick-commands"></div>
            <div class="ai-messages-container" id="ai-messages"></div>
            <div class="ai-input-container">
                <div class="ai-input-wrapper">
                    <div class="ai-input-actions">
                        <button class="ai-input-action-btn" id="ai-select-email-btn" title="选择邮件">
                            <i class="fas fa-envelope-open-text"></i>
                        </button>
                        <button class="ai-input-action-btn" id="ai-clear-context-btn" title="清空上下文（清除选中的邮件和会话记录）">
                            <i class="fas fa-broom"></i>
                        </button>
                        <button class="ai-input-action-btn" id="ai-panel-copy" title="复制对话记录">
                            <i class="fas fa-copy"></i>
                        </button>
                        <button class="ai-input-action-btn" id="ai-panel-paste" title="粘贴到输入框">
                            <i class="fas fa-paste"></i>
                        </button>
                        <button class="ai-input-action-btn" id="ai-panel-clear-history" title="清空对话历史（删除所有显示的消息）">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                        <button class="ai-input-action-btn" id="ai-edit-commands-btn" title="编辑快捷命令">
                            <i class="fas fa-edit"></i>
                        </button>
                    </div>
                    <textarea 
                        id="ai-message-input" 
                        placeholder="输入消息，例如：帮我找今天的邮件..." 
                        rows="1"
                    ></textarea>
                </div>
                <button id="ai-send-btn">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        `;
        document.body.appendChild(panel);
        
        // 缓存DOM元素
        this.trigger = trigger;
        this.panel = panel;
        this.messagesContainer = document.getElementById('ai-messages');
        this.input = document.getElementById('ai-message-input');
        this.sendBtn = document.getElementById('ai-send-btn');
        this.quickCommandsContainer = document.getElementById('ai-quick-commands');
        
        // 加载快捷指令
        this.loadQuickCommands();
    }
    
    bindEvents() {
        // 触发按钮点击
        this.trigger.addEventListener('click', () => this.toggle());
        
        // 关闭按钮（只有这个可以关闭面板）
        document.getElementById('ai-panel-close').addEventListener('click', (e) => {
            e.stopPropagation();
            this.close();
        });
        
        // 最小化按钮
        document.getElementById('ai-panel-minimize').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleMinimize();
        });
        
        // 全屏按钮
        document.getElementById('ai-panel-fullscreen').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleFullscreen();
        });
        
        // 复制对话记录按钮（阻止事件冒泡）
        document.getElementById('ai-panel-copy').addEventListener('click', (e) => {
            e.stopPropagation();
            this.copyConversation();
        });
        
        // 粘贴按钮（阻止事件冒泡）
        document.getElementById('ai-panel-paste').addEventListener('click', (e) => {
            e.stopPropagation();
            this.pasteFromClipboard();
        });
        
        // 清空历史按钮（阻止事件冒泡）
        document.getElementById('ai-panel-clear-history').addEventListener('click', (e) => {
            e.stopPropagation();
            this.clearHistory();
        });
        
        // 编辑快捷命令按钮
        document.getElementById('ai-edit-commands-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.openCommandEditor();
        });
        
        // 发送按钮
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // 输入框回车发送
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 输入框自动调整高度
        this.input.addEventListener('input', () => {
            this.input.style.height = 'auto';
            this.input.style.height = Math.min(this.input.scrollHeight, 100) + 'px';
        });
        
        // 选择邮件按钮
        document.getElementById('ai-select-email-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.openEmailSelector();
        });
        
        // 清空上下文按钮
        document.getElementById('ai-clear-context-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.clearContext();
        });
        
        // 拖拽功能
        const header = this.panel.querySelector('.ai-panel-header');
        header.addEventListener('mousedown', (e) => this.startDrag(e));
        document.addEventListener('mousemove', (e) => this.drag(e));
        document.addEventListener('mouseup', () => this.stopDrag());
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.isOpen = true;
        this.panel.classList.add('show');
        this.trigger.classList.add('active');
        this.input.focus();
    }
    
    close() {
        this.isOpen = false;
        this.panel.classList.remove('show');
        this.trigger.classList.remove('active');
    }
    
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.panel.classList.toggle('minimized');
        
        const icon = document.querySelector('#ai-panel-minimize i');
        if (this.isMinimized) {
            icon.classList.remove('fa-minus');
            icon.classList.add('fa-window-maximize');
        } else {
            icon.classList.remove('fa-window-maximize');
            icon.classList.add('fa-minus');
        }
    }
    
    toggleFullscreen() {
        this.isFullscreen = !this.isFullscreen;
        this.panel.classList.toggle('fullscreen');
        
        const icon = document.querySelector('#ai-panel-fullscreen i');
        if (this.isFullscreen) {
            icon.classList.remove('fa-expand');
            icon.classList.add('fa-compress');
            // 全屏时禁用拖拽
            this.panel.style.right = '';
            this.panel.style.bottom = '';
        } else {
            icon.classList.remove('fa-compress');
            icon.classList.add('fa-expand');
        }
    }
    
    startDrag(e) {
        this.isDragging = true;
        const rect = this.panel.getBoundingClientRect();
        this.dragOffset = {
            x: e.clientX - rect.right,
            y: e.clientY - rect.bottom
        };
    }
    
    drag(e) {
        if (!this.isDragging) return;
        
        const x = window.innerWidth - e.clientX - this.dragOffset.x;
        const y = window.innerHeight - e.clientY - this.dragOffset.y;
        
        this.panel.style.right = Math.max(10, x) + 'px';
        this.panel.style.bottom = Math.max(10, y) + 'px';
    }
    
    stopDrag() {
        this.isDragging = false;
    }
    
    clearHistory() {
        if (confirm('确定要清空所有对话历史吗？')) {
            this.messages = [];
            localStorage.removeItem('ai_assistant_messages');
            this.showWelcome();
            console.log('对话历史已清空');
        }
    }
    
    async copyConversation() {
        try {
            // 获取所有消息
            const messages = this.messagesContainer.querySelectorAll('.ai-message');
            if (messages.length === 0) {
                this.showToast('暂无对话记录可复制', 'warning');
                return;
            }
            
            // 构建对话文本
            let conversationText = '=== AI邮件助手对话记录 ===\n\n';
            
            messages.forEach((msgEl, index) => {
                const role = msgEl.classList.contains('user') ? '用户' : 'AI助手';
                const time = msgEl.querySelector('.ai-message-time')?.textContent || '';
                const textEl = msgEl.querySelector('.ai-message-text');
                
                if (textEl) {
                    let content = textEl.textContent.trim();
                    
                    // 添加角色和时间
                    conversationText += `[${role}] ${time}\n`;
                    conversationText += `${content}\n\n`;
                    
                    // 如果有邮件列表，添加邮件信息
                    const emailList = msgEl.querySelector('.ai-email-list');
                    if (emailList) {
                        const emailCards = emailList.querySelectorAll('.ai-email-card');
                        if (emailCards.length > 0) {
                            conversationText += `  相关邮件 (${emailCards.length}封):\n`;
                            emailCards.forEach((card, idx) => {
                                const subject = card.querySelector('.ai-email-card-subject')?.textContent || '';
                                const sender = card.querySelector('.ai-email-card-sender')?.textContent || '';
                                conversationText += `  ${idx + 1}. ${subject} - ${sender}\n`;
                            });
                            conversationText += '\n';
                        }
                    }
                }
                
                conversationText += '─'.repeat(50) + '\n\n';
            });
            
            conversationText += `\n总计：${messages.length} 条消息`;
            conversationText += `\n导出时间：${new Date().toLocaleString('zh-CN')}`;
            
            // 复制到剪贴板
            await navigator.clipboard.writeText(conversationText);
            
            this.showToast('✅ 对话记录已复制到剪贴板', 'success');
            console.log('复制的对话长度:', conversationText.length, '字符');
            
        } catch (error) {
            console.error('复制对话记录失败:', error);
            this.showToast('❌ 复制失败，请重试', 'error');
        }
    }
    
    async pasteFromClipboard() {
        try {
            // 读取剪贴板内容
            const text = await navigator.clipboard.readText();
            
            if (!text || text.trim() === '') {
                this.showToast('剪贴板为空', 'warning');
                return;
            }
            
            // 将内容粘贴到输入框
            const currentValue = this.input.value;
            if (currentValue && currentValue.trim() !== '') {
                // 如果输入框有内容，追加在后面
                this.input.value = currentValue + '\n' + text;
            } else {
                // 如果输入框为空，直接设置
                this.input.value = text;
            }
            
            // 调整输入框高度
            this.input.style.height = 'auto';
            this.input.style.height = Math.min(this.input.scrollHeight, 200) + 'px';
            
            // 聚焦到输入框
            this.input.focus();
            
            // 移动光标到末尾
            this.input.selectionStart = this.input.selectionEnd = this.input.value.length;
            
            this.showToast(`✅ 已粘贴 ${text.length} 个字符`, 'success');
            console.log('粘贴内容长度:', text.length, '字符');
            
        } catch (error) {
            console.error('粘贴失败:', error);
            
            // 如果是权限问题，给出提示
            if (error.name === 'NotAllowedError') {
                this.showToast('❌ 需要剪贴板权限。请在浏览器中允许访问剪贴板', 'error');
            } else {
                this.showToast('❌ 粘贴失败，请重试', 'error');
            }
        }
    }
    
    showToast(message, type = 'info') {
        // 创建toast元素
        const toast = document.createElement('div');
        toast.className = `ai-toast ai-toast-${type}`;
        toast.textContent = message;
        
        // 添加样式
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10001;
            animation: slideInRight 0.3s ease-out;
            font-size: 14px;
            max-width: 300px;
        `;
        
        document.body.appendChild(toast);
        
        // 3秒后自动移除
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    checkStorageUsage() {
        try {
            let totalSize = 0;
            for (let key in localStorage) {
                if (localStorage.hasOwnProperty(key)) {
                    totalSize += localStorage[key].length + key.length;
                }
            }
            const usageMB = (totalSize / 1024 / 1024).toFixed(2);
            console.log(`LocalStorage使用量: ${usageMB}MB / ~5MB`);
            
            // 如果使用超过4MB，警告用户
            if (totalSize > 4 * 1024 * 1024) {
                console.warn('LocalStorage使用量较高，建议清理对话历史');
            }
        } catch (error) {
            console.error('检查存储使用量失败:', error);
        }
    }
    
    async loadQuickCommands() {
        // 从本地存储加载快捷命令，如果没有则使用默认命令
        let commands = this.getStoredCommands();
        if (!commands || commands.length === 0) {
            commands = this.getDefaultCommands();
            this.saveCommands(commands);
        }
        this.renderQuickCommands(commands);
    }
    
    getDefaultCommands() {
        // 默认快捷命令（去重并增加新类型）
        return [
            { id: 1, text: '今天的邮件', icon: 'fa-calendar-day', category: '时间' },
            { id: 2, text: '近三天的邮件', icon: 'fa-clock', category: '时间' },
            { id: 3, text: '本周的邮件', icon: 'fa-calendar-week', category: '时间' },
            { id: 4, text: '重要邮件', icon: 'fa-star', category: '重要性' },
            { id: 5, text: '未读邮件', icon: 'fa-envelope', category: '状态' },
            { id: 6, text: '工作邮件', icon: 'fa-briefcase', category: '分类' },
            { id: 7, text: '财务邮件', icon: 'fa-dollar-sign', category: '分类' },
            { id: 8, text: '本周统计', icon: 'fa-chart-bar', category: '统计' },
            { id: 9, text: '今天收到多少邮件', icon: 'fa-chart-pie', category: '统计' },
            { id: 10, text: '工作邮件并且重要的', icon: 'fa-filter', category: '综合' },
            { id: 11, text: '最近三天未读的工作邮件', icon: 'fa-search', category: '综合' }
        ];
    }
    
    getStoredCommands() {
        try {
            const stored = localStorage.getItem('ai_quick_commands');
            return stored ? JSON.parse(stored) : null;
        } catch (error) {
            console.error('读取快捷命令失败:', error);
            return null;
        }
    }
    
    saveCommands(commands) {
        try {
            localStorage.setItem('ai_quick_commands', JSON.stringify(commands));
        } catch (error) {
            console.error('保存快捷命令失败:', error);
        }
    }
    
    renderQuickCommands(commands) {
        this.quickCommandsContainer.innerHTML = commands.map(cmd => `
            <button class="ai-quick-command" data-command="${cmd.text}" data-id="${cmd.id}">
                <i class="fas ${cmd.icon}"></i>
                <span>${cmd.text}</span>
            </button>
        `).join('');
        
        // 绑定点击事件
        this.quickCommandsContainer.querySelectorAll('.ai-quick-command').forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.getAttribute('data-command');
                this.input.value = command;
                this.sendMessage();
            });
        });
    }
    
    showWelcome() {
        // 欢迎信息已移到顶部，这里只需清空消息容器
        this.messagesContainer.innerHTML = '';
    }
    
    async sendMessage() {
        const message = this.input.value.trim();
        if (!message) return;
        
        // 清空输入框
        this.input.value = '';
        this.input.style.height = 'auto';
        
        // 显示用户消息
        this.addMessage('user', message);
        
        // 显示思考状态
        const thinkingId = this.addThinkingMessage();
        
        // 禁用发送按钮
        this.sendBtn.disabled = true;
        
        try {
            // 发送请求
            const response = await fetch('/api/ai-assistant/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    context: this.context
                })
            });
            
            const data = await response.json();
            
            // 移除思考状态
            this.removeMessage(thinkingId);
            
            if (data.success) {
                // 调试日志：查看返回的数据
                console.log('📧 AI助手返回数据:', {
                    response: data.response?.substring(0, 100),
                    emails_count: data.emails?.length || 0,
                    statistics: data.statistics ? '有统计' : '无统计',
                    actions: data.actions?.length || 0,
                    last_cached_emails: this.lastEmails.length
                });
                
                // 如果有新邮件，更新缓存
                if (data.emails && data.emails.length > 0) {
                    this.lastEmails = data.emails;
                    this.lastEmailSearchQuery = message;
                    console.log('💾 缓存邮件列表:', this.lastEmails.length, '封');
                }
                
                // 智能决策：是否显示缓存的邮件
                let emailsToShow = data.emails || [];
                
                if (emailsToShow.length === 0 && this.lastEmails.length > 0) {
                    // 检测回答是否涉及邮件内容
                    const emailKeywords = [
                        '邮件', '发件人', '主题', '内容', '附件',
                        '第一封', '第二封', '第三封', '第四封', '第五封',
                        '这封', '那封', '最近', '最新', '之前', '上面',
                        '谁发的', '什么时候', '关于什么', '说了什么'
                    ];
                    
                    const isEmailRelated = emailKeywords.some(keyword => 
                        data.response.includes(keyword)
                    );
                    
                    if (isEmailRelated) {
                        console.log('📎 使用缓存的邮件列表 (检测到邮件相关回答)');
                        emailsToShow = this.lastEmails;
                    }
                }
                
                // 显示AI回复
                this.addMessage('assistant', data.response, {
                    emails: emailsToShow,
                    actions: data.actions,
                    statistics: data.statistics
                });
                
                // 更新对话历史
                this.context.conversation_history.push(
                    { role: 'user', content: message },
                    { role: 'assistant', content: data.response }
                );
                
                // 保存历史
                this.saveHistory();
            } else {
                this.addMessage('assistant', '抱歉，处理您的请求时出现了错误。请稍后再试。', {
                    isError: true
                });
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            this.removeMessage(thinkingId);
            this.addMessage('assistant', '网络连接失败，请检查您的网络连接后重试。', {
                isError: true
            });
        } finally {
            // 启用发送按钮
            this.sendBtn.disabled = false;
            this.input.focus();
        }
    }
    
    addMessage(role, content, options = {}) {
        const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        
        // 如果是第一条消息，清除欢迎界面
        if (this.messagesContainer.querySelector('.ai-welcome-message')) {
            this.messagesContainer.innerHTML = '';
        }
        
        const messageEl = document.createElement('div');
        messageEl.className = `ai-message ${role}`;
        messageEl.id = messageId;
        
        const avatar = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        let contentHtml = `<div class="ai-message-text">${this.escapeHtml(content)}</div>`;
        
        // 添加邮件列表
        if (options.emails && options.emails.length > 0) {
            contentHtml += this.renderEmailList(options.emails);
        }
        
        // 添加统计信息
        if (options.statistics) {
            contentHtml += this.renderStatistics(options.statistics);
        }
        
        // 添加操作按钮
        if (options.actions && options.actions.length > 0) {
            contentHtml += this.renderActions(options.actions);
        }
        
        // 错误样式
        const errorClass = options.isError ? ' ai-error-message' : '';
        
        messageEl.innerHTML = `
            <div class="ai-message-avatar">${avatar}</div>
            <div class="ai-message-content${errorClass}">
                ${contentHtml}
                <div class="ai-message-time">${time}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageEl);
        this.scrollToBottom();
        
        this.messages.push({
            id: messageId,
            role: role,
            content: content,
            time: time,
            options: options
        });
        
        return messageId;
    }
    
    addThinkingMessage() {
        const messageId = `thinking-${Date.now()}`;
        
        const messageEl = document.createElement('div');
        messageEl.className = 'ai-message assistant thinking';
        messageEl.id = messageId;
        
        messageEl.innerHTML = `
            <div class="ai-message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="ai-message-content">
                <span>正在思考</span>
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageEl);
        this.scrollToBottom();
        
        return messageId;
    }
    
    removeMessage(messageId) {
        const messageEl = document.getElementById(messageId);
        if (messageEl) {
            messageEl.remove();
        }
    }
    
    renderEmailList(emails) {
        if (emails.length === 0) return '';
        
        const MAX_SHOW = 5;
        const showEmails = emails.slice(0, MAX_SHOW);
        const hasMore = emails.length > MAX_SHOW;
        
        const emailsHtml = showEmails.map(email => this.renderEmailCard(email)).join('');
        
        return `
            <div class="ai-email-list">
                <div class="ai-email-list-header">
                    <span class="ai-email-list-count">共 ${emails.length} 封邮件</span>
                    ${hasMore ? `<button class="ai-email-list-toggle" onclick="aiAssistant.showMoreEmails(${JSON.stringify(emails).replace(/"/g, '&quot;')})">查看全部</button>` : ''}
                </div>
                ${emailsHtml}
            </div>
        `;
    }
    
    renderEmailCard(email) {
        const categoryColors = {
            'work': '#4299E1',
            'finance': '#48BB78',
            'social': '#ED8936',
            'shopping': '#9F7AEA',
            'news': '#ECC94B',
            'general': '#A0AEC0'
        };
        
        const categoryColor = categoryColors[email.category] || categoryColors['general'];
        const date = new Date(email.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
        const summary = email.summary || email.ai_summary || email.body_preview || (email.body ? email.body.substring(0, 100) : '暂无内容');
        
        return `
            <div class="ai-email-card" onclick="aiAssistant.openEmail(${email.id})">
                <div class="ai-email-card-header">
                    <div class="ai-email-card-category" style="background: ${categoryColor}"></div>
                    <div class="ai-email-card-subject">${this.escapeHtml(email.subject)}</div>
                    <div class="ai-email-card-date">${date}</div>
                </div>
                <div class="ai-email-card-sender">${this.escapeHtml(email.sender)}</div>
                <div class="ai-email-card-summary">${this.escapeHtml(summary)}</div>
            </div>
        `;
    }
    
    renderStatistics(statistics) {
        if (!statistics || !statistics.by_category) return '';
        
        const categoryNames = {
            'work': '工作',
            'finance': '金融',
            'social': '社交',
            'shopping': '购物',
            'news': '新闻',
            'general': '通用'
        };
        
        const items = Object.entries(statistics.by_category)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([category, count]) => `
                <div class="ai-statistics-item">
                    <span class="ai-statistics-label">${categoryNames[category] || category}</span>
                    <span class="ai-statistics-value">${count} 封</span>
                </div>
            `).join('');
        
        return `
            <div class="ai-statistics">
                <div class="ai-statistics-title">
                    <i class="fas fa-chart-pie"></i>
                    <span>分类统计</span>
                </div>
                <div class="ai-statistics-list">
                    ${items}
                </div>
            </div>
        `;
    }
    
    renderActions(actions) {
        const actionsHtml = actions.map(action => `
            <button class="ai-action-btn" onclick="aiAssistant.handleAction('${action.type}', ${JSON.stringify(action).replace(/"/g, '&quot;')})">
                <i class="fas ${this.getActionIcon(action.type)}"></i>
                <span>${action.label}</span>
            </button>
        `).join('');
        
        return `
            <div class="ai-action-buttons">
                ${actionsHtml}
            </div>
        `;
    }
    
    getActionIcon(actionType) {
        const icons = {
            'select_email': 'fa-envelope-open-text',
            'generate_reply': 'fa-reply',
            'open_compose': 'fa-pen',
            'view_details': 'fa-info-circle'
        };
        return icons[actionType] || 'fa-bolt';
    }
    
    handleAction(actionType, actionData) {
        console.log('执行操作:', actionType, actionData);
        
        switch (actionType) {
            case 'select_email':
                this.openEmailSelector();
                break;
            case 'generate_reply':
                this.generateReply(actionData.email_id);
                break;
            case 'open_compose':
                this.openCompose(actionData.email_id);
                break;
            default:
                console.warn('未知操作类型:', actionType);
        }
    }
    
    async openEmail(emailId) {
        // 打开邮件详情模态框
        try {
            const response = await fetch(`/api/emails/${emailId}`);
            const data = await response.json();
            
            if (!data.success || !data.email) {
                alert('无法加载邮件详情');
                return;
            }
            
            const email = data.email;
            
            // 创建详情模态框
            const modal = document.createElement('div');
            modal.className = 'ai-email-detail-overlay';
            modal.innerHTML = `
                <div class="ai-email-detail-modal">
                    <div class="ai-email-detail-header">
                        <div class="ai-email-detail-title">邮件详情</div>
                        <button class="ai-email-detail-close">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="ai-email-detail-content">
                        <div class="ai-email-detail-subject">
                            <h4>${this.escapeHtml(email.subject)}</h4>
                        </div>
                        <div class="ai-email-detail-meta">
                            <div class="ai-email-detail-meta-item">
                                <strong>发件人：</strong>
                                <span>${this.escapeHtml(email.sender)}</span>
                            </div>
                            <div class="ai-email-detail-meta-item">
                                <strong>收件人：</strong>
                                <span>${this.escapeHtml(email.account_email)}</span>
                            </div>
                            <div class="ai-email-detail-meta-item">
                                <strong>时间：</strong>
                                <span>${new Date(email.date).toLocaleString('zh-CN')}</span>
                            </div>
                            ${email.category ? `
                            <div class="ai-email-detail-meta-item">
                                <strong>分类：</strong>
                                <span class="badge bg-primary">${this.getCategoryName(email.category)}</span>
                            </div>
                            ` : ''}
                        </div>
                        ${email.ai_summary || email.summary ? `
                        <div class="ai-email-detail-summary">
                            <h5><i class="fas fa-lightbulb me-2"></i>AI摘要</h5>
                            <p>${this.escapeHtml(email.ai_summary || email.summary)}</p>
                        </div>
                        ` : ''}
                        <div class="ai-email-detail-body">
                            <h5><i class="fas fa-align-left me-2"></i>邮件正文</h5>
                            <div class="ai-email-detail-body-content">
                                ${email.body_html || this.escapeHtml(email.body).replace(/\n/g, '<br>')}
                            </div>
                        </div>
                        ${email.attachments && email.attachments.length > 0 ? `
                        <div class="ai-email-detail-attachments">
                            <h5><i class="fas fa-paperclip me-2"></i>附件 (${email.attachments.length})</h5>
                            <div class="ai-email-detail-attachments-list">
                                ${email.attachments.map(att => `
                                    <div class="ai-email-detail-attachment-item">
                                        <i class="fas fa-file"></i>
                                        <span>${this.escapeHtml(att.filename || att)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="ai-email-detail-footer">
                        <button class="ai-email-detail-btn" onclick="window.location.href='/emails?highlight=${emailId}'">
                            <i class="fas fa-external-link-alt me-2"></i>在邮件列表中查看
                        </button>
                        <button class="ai-email-detail-btn primary" onclick="window.location.href='/compose?reply_to=${emailId}'">
                            <i class="fas fa-reply me-2"></i>回复
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // 绑定关闭事件
            const closeBtn = modal.querySelector('.ai-email-detail-close');
            const close = () => {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
            };
            
            closeBtn.addEventListener('click', close);
            modal.addEventListener('click', (e) => {
                if (e.target === modal) close();
            });
            
            // 显示模态框
            setTimeout(() => modal.classList.add('show'), 10);
            
        } catch (error) {
            console.error('加载邮件详情失败:', error);
            alert('加载邮件详情失败');
        }
    }
    
    getCategoryName(category) {
        const names = {
            'work': '工作',
            'finance': '金融',
            'social': '社交',
            'shopping': '购物',
            'news': '新闻',
            'general': '通用'
        };
        return names[category] || category;
    }
    
    showMoreEmails(emails) {
        // 在新窗口中显示所有检索结果的邮件
        // 生成HTML内容
        const htmlContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI邮件助手 - 检索结果（${emails.length}封）</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #F7FAFC;
            padding: 16px;
        }
        .header {
            background: white;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 16px;
            font-weight: 600;
            color: #2D3748;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .header h1 i { color: #4A90E2; font-size: 18px; }
        .count {
            font-size: 12px;
            color: #718096;
            background: #EDF2F7;
            padding: 4px 10px;
            border-radius: 12px;
        }
        .email-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .email-item {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 8px 12px;
            transition: all 0.2s;
            cursor: pointer;
        }
        .email-item:hover {
            border-color: #4A90E2;
            box-shadow: 0 2px 8px rgba(74,144,226,0.15);
            transform: translateX(2px);
        }
        .email-item.unread {
            border-left: 3px solid #4A90E2;
            background: linear-gradient(90deg, rgba(74,144,226,0.03) 0%, white 30%);
        }
        .email-item.unread .email-subject { color: #4A90E2; font-weight: 600; }
        
        /* 第一行：标签、主题、日期 */
        .email-row1 {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .email-category {
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 8px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .email-subject {
            font-size: 13px;
            color: #2D3748;
            font-weight: 500;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .email-badges {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
        .badge {
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 8px;
            font-weight: 600;
        }
        .badge.unread { background: #4A90E2; color: white; }
        .badge.high { background: #FED7D7; color: #C53030; }
        .badge.medium { background: #FEEBC8; color: #C05621; }
        .email-date {
            font-size: 11px;
            color: #A0AEC0;
            white-space: nowrap;
            flex-shrink: 0;
        }
        
        /* 第二行：发件人、账户、按钮 */
        .email-row2 {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 11px;
            color: #718096;
        }
        .email-sender {
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
        }
        .email-sender i { font-size: 10px; color: #A0AEC0; }
        .email-account {
            display: flex;
            align-items: center;
            gap: 4px;
            color: #A0AEC0;
            flex: 1;
            overflow: hidden;
        }
        .email-account i { font-size: 9px; }
        .email-account span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .email-actions {
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }
        .email-btn {
            padding: 3px 10px;
            border: 1px solid #E2E8F0;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 11px;
            color: #4A5568;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .email-btn:hover {
            background: #4A90E2;
            border-color: #4A90E2;
            color: white;
        }
        .email-btn i { font-size: 10px; }
        
        .empty {
            text-align: center;
            padding: 60px;
            color: #A0AEC0;
        }
        .empty i { font-size: 48px; opacity: 0.5; margin-bottom: 12px; }
        
        /* 邮件详情模态框样式 */
        .email-detail-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        }
        .email-detail-overlay.show { display: flex; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        
        .email-detail-modal {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            animation: slideInUp 0.3s ease;
        }
        @keyframes slideInUp {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .email-detail-header {
            padding: 20px 24px;
            border-bottom: 2px solid #E2E8F0;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        .email-detail-title { flex: 1; }
        .email-detail-title h3 {
            font-size: 18px;
            font-weight: 600;
            color: #2D3748;
            margin-bottom: 12px;
        }
        .email-detail-meta {
            display: flex;
            flex-direction: column;
            gap: 8px;
            font-size: 13px;
            color: #718096;
        }
        .email-detail-meta-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .email-detail-meta-item i { color: #A0AEC0; width: 16px; }
        .email-detail-close {
            background: none;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            color: #718096;
            font-size: 20px;
            transition: all 0.2s;
        }
        .email-detail-close:hover {
            background: #FED7D7;
            color: #C53030;
        }
        
        .email-detail-body {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }
        .email-detail-content {
            font-size: 14px;
            color: #4A5568;
            line-height: 1.6;
        }
        
        .email-detail-footer {
            padding: 16px 24px;
            border-top: 1px solid #E2E8F0;
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        .email-detail-btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid #E2E8F0;
            background: white;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .email-detail-btn:hover {
            background: #F7FAFC;
            border-color: #4A90E2;
            color: #4A90E2;
        }
        .email-detail-btn.primary {
            background: #4A90E2;
            color: white;
            border-color: #4A90E2;
        }
        .email-detail-btn.primary:hover {
            background: #667EEA;
            border-color: #667EEA;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-envelope-open-text"></i> 邮件检索结果</h1>
        <span class="count">共 ${emails.length} 封邮件</span>
    </div>
    <div class="email-list">
        ${this.renderCompactEmailList(emails)}
    </div>
    
    <!-- 邮件详情模态框 -->
    <div class="email-detail-overlay" id="emailDetailOverlay">
        <div class="email-detail-modal">
            <div class="email-detail-header">
                <div class="email-detail-title">
                    <h3 id="detailSubject">邮件主题</h3>
                    <div class="email-detail-meta">
                        <div class="email-detail-meta-item">
                            <i class="fas fa-user"></i>
                            <span id="detailSender">发件人</span>
                        </div>
                        <div class="email-detail-meta-item">
                            <i class="fas fa-clock"></i>
                            <span id="detailDate">时间</span>
                        </div>
                        <div class="email-detail-meta-item">
                            <i class="fas fa-at"></i>
                            <span id="detailAccount">账户</span>
                        </div>
                    </div>
                </div>
                <button class="email-detail-close" onclick="closeEmailDetail()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="email-detail-body">
                <div class="email-detail-content" id="detailBody">
                    正在加载...
                </div>
            </div>
            <div class="email-detail-footer">
                <button class="email-detail-btn" onclick="closeEmailDetail()">
                    <i class="fas fa-times"></i> 关闭
                </button>
                <button class="email-detail-btn primary" id="detailReplyBtn">
                    <i class="fas fa-reply"></i> 回复
                </button>
            </div>
        </div>
    </div>
    
    <script>
        // 打开邮件详情
        async function openEmail(emailId) {
            const overlay = document.getElementById('emailDetailOverlay');
            overlay.classList.add('show');
            
            try {
                // 从主窗口获取邮件详情
                const response = await fetch('/api/emails/' + emailId);
                const data = await response.json();
                
                if (data.success && data.email) {
                    const email = data.email;
                    
                    // 更新模态框内容
                    document.getElementById('detailSubject').textContent = email.subject || '(无主题)';
                    document.getElementById('detailSender').textContent = email.sender || '未知';
                    
                    // 格式化日期
                    const date = email.date ? new Date(email.date) : new Date();
                    document.getElementById('detailDate').textContent = date.toLocaleString('zh-CN');
                    
                    document.getElementById('detailAccount').textContent = email.account || email.to || '';
                    
                    // 处理邮件正文
                    let body = email.body || '';
                    if (body.includes('<html') || body.includes('<body')) {
                        // HTML邮件，直接显示
                        document.getElementById('detailBody').innerHTML = body;
                    } else {
                        // 纯文本邮件，转换换行符
                        body = body.replace(/\\n/g, '<br>').replace(/\\r/g, '');
                        document.getElementById('detailBody').innerHTML = body;
                    }
                    
                    // 设置回复按钮
                    document.getElementById('detailReplyBtn').onclick = () => replyEmail(emailId);
                } else {
                    document.getElementById('detailBody').innerHTML = '<p style="color: #E53E3E;">加载邮件详情失败</p>';
                }
            } catch (error) {
                console.error('加载邮件详情失败:', error);
                document.getElementById('detailBody').innerHTML = '<p style="color: #E53E3E;">加载失败: ' + error.message + '</p>';
            }
        }
        
        // 关闭邮件详情
        function closeEmailDetail() {
            document.getElementById('emailDetailOverlay').classList.remove('show');
        }
        
        // 回复邮件（在新标签页打开）
        function replyEmail(emailId) {
            window.open('/compose?reply_to=' + emailId, '_blank');
        }
        
        // 点击遮罩关闭
        document.getElementById('emailDetailOverlay').addEventListener('click', function(e) {
            if (e.target === this) {
                closeEmailDetail();
            }
        });
        
        // ESC键关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeEmailDetail();
            }
        });
    </script>
</body>
</html>`;
        
        // 打开新窗口
        const newWindow = window.open('', '_blank', 'width=1000,height=800,menubar=no,toolbar=no,location=no,status=no');
        if (newWindow) {
            newWindow.document.write(htmlContent);
            newWindow.document.close();
        } else {
            alert('请允许弹出窗口以查看邮件检索结果');
        }
    }
    
    renderCompactEmailList(emails) {
        // 渲染紧凑的邮件列表（2行布局）
        if (!emails || emails.length === 0) {
            return `
                <div class="empty">
                    <i class="fas fa-inbox"></i>
                    <p>没有找到邮件</p>
                </div>
            `;
        }
        
        const categoryColors = {
            'work': '#4299E1', 'finance': '#48BB78', 'social': '#9F7AEA',
            'shopping': '#F56565', 'news': '#ED8936', 'education': '#38B2AC',
            'travel': '#3182CE', 'health': '#D53F8C', 'system': '#718096',
            'advertising': '#DD6B20', 'spam': '#E53E3E', 'general': '#A0AEC0'
        };
        
        const categoryNames = {
            'work': '工作', 'finance': '财务', 'social': '社交',
            'shopping': '购物', 'news': '新闻', 'education': '教育',
            'travel': '旅行', 'health': '健康', 'system': '系统',
            'advertising': '广告', 'spam': '垃圾', 'general': '通用'
        };
        
        return emails.map(email => {
            const category = email.category || 'general';
            const categoryColor = categoryColors[category] || '#A0AEC0';
            const categoryName = categoryNames[category] || '通用';
            
            // 处理发件人
            let senderDisplay = email.sender || '未知';
            if (senderDisplay.includes('<')) {
                senderDisplay = senderDisplay.split('<')[0].trim().replace(/"/g, '');
            }
            if (senderDisplay.length > 20) {
                senderDisplay = senderDisplay.substring(0, 20) + '...';
            }
            
            // 处理收件账户
            const account = email.account || email.to || '';
            
            // 处理日期（短格式）
            const date = email.date ? new Date(email.date) : new Date();
            const now = new Date();
            const isToday = date.toDateString() === now.toDateString();
            const dateStr = isToday 
                ? date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                : date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
            
            // 处理主题
            const subject = email.subject || '(无主题)';
            
            // 未读和重要性标记
            const unreadClass = email.is_read === 0 ? 'unread' : '';
            const unreadBadge = email.is_read === 0 ? '<span class="badge unread">未读</span>' : '';
            
            let importanceBadge = '';
            if (email.importance >= 3) {
                importanceBadge = '<span class="badge high">紧急</span>';
            } else if (email.importance >= 2) {
                importanceBadge = '<span class="badge medium">重要</span>';
            }
            
            return `
                <div class="email-item ${unreadClass}" onclick="openEmail(${email.id})">
                    <div class="email-row1">
                        <span class="email-category" style="background: ${categoryColor}20; color: ${categoryColor};">
                            ${categoryName}
                        </span>
                        <span class="email-subject">${this.escapeHtml(subject)}</span>
                        <div class="email-badges">
                            ${unreadBadge}
                            ${importanceBadge}
                        </div>
                        <span class="email-date">${dateStr}</span>
                    </div>
                    <div class="email-row2">
                        <span class="email-sender">
                            <i class="fas fa-user"></i>
                            ${this.escapeHtml(senderDisplay)}
                        </span>
                        <span class="email-account">
                            <i class="fas fa-at"></i>
                            <span>${this.escapeHtml(account)}</span>
                        </span>
                        <div class="email-actions">
                            <button class="email-btn" onclick="event.stopPropagation(); openEmail(${email.id})">
                                <i class="fas fa-eye"></i> 查看
                            </button>
                            <button class="email-btn" onclick="event.stopPropagation(); replyEmail(${email.id})">
                                <i class="fas fa-reply"></i> 回复
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    async openEmailSelector() {
        // 创建邮件选择器模态框
        const overlay = document.createElement('div');
        overlay.className = 'ai-email-selector-overlay';
        overlay.innerHTML = `
            <div class="ai-email-selector-modal">
                <div class="ai-email-selector-header">
                    <div class="ai-email-selector-title">
                        <i class="fas fa-envelope-open-text me-2"></i>
                        选择邮件
                    </div>
                    <button class="ai-email-selector-close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="ai-email-selector-search">
                    <input type="text" placeholder="搜索邮件标题、发件人..." id="ai-email-search-input">
                </div>
                <div class="ai-email-selector-list" id="ai-email-selector-list">
                    <div class="ai-email-selector-loading">
                        <i class="fas fa-spinner fa-spin"></i>
                        <p>正在加载邮件...</p>
                    </div>
                </div>
                <div class="ai-email-selector-footer">
                    <div class="ai-email-selector-count">
                        已选择 <span id="ai-email-selected-count">0</span> 封邮件
                    </div>
                    <div class="ai-email-selector-actions">
                        <button class="ai-email-selector-btn cancel">取消</button>
                        <button class="ai-email-selector-btn confirm" id="ai-email-confirm-btn">确认选择</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 加载邮件列表
        await this.loadEmailsForSelector();
        
        // 绑定事件
        const closeBtn = overlay.querySelector('.ai-email-selector-close');
        const cancelBtn = overlay.querySelector('.cancel');
        const confirmBtn = overlay.querySelector('#ai-email-confirm-btn');
        const searchInput = overlay.querySelector('#ai-email-search-input');
        
        const close = () => {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
        };
        
        closeBtn.addEventListener('click', close);
        cancelBtn.addEventListener('click', close);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) close();
        });
        
        confirmBtn.addEventListener('click', () => {
            const selected = Array.from(overlay.querySelectorAll('.ai-email-selector-item.selected'))
                .map(item => parseInt(item.dataset.emailId));
            
            if (selected.length > 0) {
                this.context.selected_email_ids = selected;
                this.input.value = `已选择 ${selected.length} 封邮件，请问需要我帮您做什么？`;
                close();
                this.input.focus();
            }
        });
        
        // 搜索功能
        searchInput.addEventListener('input', (e) => {
            this.filterEmailSelector(e.target.value);
        });
        
        // 显示模态框
        setTimeout(() => overlay.classList.add('show'), 10);
    }
    
    async loadEmailsForSelector() {
        try {
            const response = await fetch('/api/emails?limit=100');
            const data = await response.json();
            
            const listContainer = document.getElementById('ai-email-selector-list');
            
            if (!data.success || !data.emails || data.emails.length === 0) {
                listContainer.innerHTML = `
                    <div class="ai-email-selector-empty">
                        <i class="fas fa-inbox"></i>
                        <p>暂无邮件</p>
                    </div>
                `;
                return;
            }
            
            // 按时间倒序排列
            const emails = data.emails.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            listContainer.innerHTML = emails.map(email => {
                const date = new Date(email.date).toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                return `
                    <div class="ai-email-selector-item" data-email-id="${email.id}">
                        <div class="ai-email-selector-checkbox">
                            <i class="fas fa-check"></i>
                        </div>
                        <div class="ai-email-selector-info">
                            <div class="ai-email-selector-subject">${this.escapeHtml(email.subject)}</div>
                            <div class="ai-email-selector-meta">
                                <span><i class="fas fa-user"></i> ${this.escapeHtml(email.sender)}</span>
                                <span><i class="fas fa-clock"></i> ${date}</span>
                                <span><i class="fas fa-envelope"></i> ${this.escapeHtml(email.account_email)}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            // 绑定点击事件
            listContainer.querySelectorAll('.ai-email-selector-item').forEach(item => {
                item.addEventListener('click', () => {
                    item.classList.toggle('selected');
                    this.updateSelectedCount();
                });
            });
            
        } catch (error) {
            console.error('加载邮件失败:', error);
            const listContainer = document.getElementById('ai-email-selector-list');
            listContainer.innerHTML = `
                <div class="ai-email-selector-empty">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>加载邮件失败</p>
                </div>
            `;
        }
    }
    
    updateSelectedCount() {
        const count = document.querySelectorAll('.ai-email-selector-item.selected').length;
        const countEl = document.getElementById('ai-email-selected-count');
        if (countEl) {
            countEl.textContent = count;
        }
        
        const confirmBtn = document.getElementById('ai-email-confirm-btn');
        if (confirmBtn) {
            confirmBtn.disabled = count === 0;
        }
    }
    
    filterEmailSelector(keyword) {
        const items = document.querySelectorAll('.ai-email-selector-item');
        const lowerKeyword = keyword.toLowerCase();
        
        items.forEach(item => {
            const subject = item.querySelector('.ai-email-selector-subject').textContent.toLowerCase();
            const meta = item.querySelector('.ai-email-selector-meta').textContent.toLowerCase();
            
            if (subject.includes(lowerKeyword) || meta.includes(lowerKeyword)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    clearContext() {
        this.context = {
            selected_email_ids: [],
            conversation_history: []
        };
        
        // 清空邮件缓存
        this.lastEmails = [];
        this.lastEmailSearchQuery = '';
        console.log('🧹 已清空上下文和邮件缓存');
        
        // 显示提示
        const toast = document.createElement('div');
        toast.className = 'ai-toast';
        toast.textContent = '上下文已清空';
        toast.style.cssText = `
            position: fixed;
            bottom: 120px;
            right: 30px;
            background: #48BB78;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 1001;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 2000);
    }
    
    generateReply(emailId) {
        // TODO: 调用回复生成API
        console.log('生成回复:', emailId);
    }
    
    openCompose(emailId) {
        // 跳转到撰写页面
        window.location.href = `/compose?reply_to=${emailId}`;
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    loadHistory() {
        try {
            const history = localStorage.getItem('ai_assistant_messages');
            if (history) {
                this.messages = JSON.parse(history);
                // 恢复消息显示
                // this.messages.forEach(msg => {
                //     this.addMessage(msg.role, msg.content, msg.options);
                // });
            }
        } catch (error) {
            console.error('加载对话历史失败:', error);
        }
    }
    
    saveHistory() {
        try {
            // 只保存最近20条消息（减少存储量）
            const recentMessages = this.messages.slice(-20);
            
            // 优化存储：移除邮件详细内容，只保留基本信息
            const optimizedMessages = recentMessages.map(msg => {
                const optimized = {
                    role: msg.role,
                    content: msg.content
                };
                
                // 如果有邮件列表，只保留基本信息（标题、ID）
                if (msg.options && msg.options.emails) {
                    optimized.options = {
                        ...msg.options,
                        emails: msg.options.emails.map(email => ({
                            id: email.id,
                            subject: email.subject ? email.subject.substring(0, 100) : '', // 限制标题长度
                            sender: email.sender,
                            date: email.date
                            // 移除 body、ai_summary 等大内容字段
                        }))
                    };
                }
                
                return optimized;
            });
            
            // 计算存储大小
            const dataSize = JSON.stringify(optimizedMessages).length;
            console.log(`保存对话历史: ${recentMessages.length}条消息, 约${(dataSize/1024).toFixed(2)}KB`);
            
            // 检查是否超过限制（4MB）
            if (dataSize > 4 * 1024 * 1024) {
                console.warn('对话历史过大，只保存最近10条');
                const smallerMessages = optimizedMessages.slice(-10);
                localStorage.setItem('ai_assistant_messages', JSON.stringify(smallerMessages));
            } else {
                localStorage.setItem('ai_assistant_messages', JSON.stringify(optimizedMessages));
            }
        } catch (error) {
            if (error.name === 'QuotaExceededError') {
                console.warn('LocalStorage空间不足，清理对话历史');
                try {
                    // 只保存最近5条消息
                    const minimalMessages = this.messages.slice(-5).map(msg => ({
                        role: msg.role,
                        content: msg.content.substring(0, 500) // 限制内容长度
                    }));
                    localStorage.setItem('ai_assistant_messages', JSON.stringify(minimalMessages));
                } catch (e) {
                    console.error('无法保存对话历史，清空存储');
                    localStorage.removeItem('ai_assistant_messages');
                }
            } else {
                console.error('保存对话历史失败:', error);
            }
        }
    }
    
    openCommandEditor() {
        // 创建编辑器模态框
        const overlay = document.createElement('div');
        overlay.className = 'ai-command-editor-overlay';
        overlay.id = 'ai-command-editor-overlay';
        
        const commands = this.getStoredCommands() || this.getDefaultCommands();
        
        overlay.innerHTML = `
            <div class="ai-command-editor-modal">
                <div class="ai-command-editor-header">
                    <h3><i class="fas fa-edit"></i> 编辑快捷命令</h3>
                    <button class="ai-command-editor-close" onclick="aiAssistant.closeCommandEditor()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="ai-command-editor-body" id="commandEditorBody">
                    ${this.renderCommandList(commands)}
                </div>
                <div class="ai-command-editor-footer">
                    <button class="ai-command-editor-btn" onclick="aiAssistant.addNewCommand()">
                        <i class="fas fa-plus"></i> 添加新命令
                    </button>
                    <button class="ai-command-editor-btn" onclick="aiAssistant.resetCommands()">
                        <i class="fas fa-undo"></i> 恢复默认
                    </button>
                    <button class="ai-command-editor-btn primary" onclick="aiAssistant.saveAndCloseEditor()">
                        <i class="fas fa-save"></i> 保存并关闭
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 点击遮罩关闭
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.closeCommandEditor();
            }
        });
    }
    
    renderCommandList(commands) {
        return `
            <div class="ai-command-list">
                ${commands.map(cmd => `
                    <div class="ai-command-item" data-id="${cmd.id}">
                        <div class="ai-command-item-icon">
                            <i class="fas ${cmd.icon}"></i>
                        </div>
                        <div class="ai-command-item-content">
                            <input type="text" class="ai-command-input" value="${cmd.text}" data-field="text">
                            <div class="ai-command-item-meta">
                                <span class="ai-command-category">${cmd.category || '通用'}</span>
                            </div>
                        </div>
                        <div class="ai-command-item-actions">
                            <button class="ai-command-item-btn" onclick="aiAssistant.editCommandIcon(${cmd.id})" title="修改图标">
                                <i class="fas fa-icons"></i>
                            </button>
                            <button class="ai-command-item-btn" onclick="aiAssistant.deleteCommand(${cmd.id})" title="删除">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    closeCommandEditor() {
        const overlay = document.getElementById('ai-command-editor-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    saveAndCloseEditor() {
        // 收集所有命令
        const commandItems = document.querySelectorAll('.ai-command-item');
        const commands = [];
        
        commandItems.forEach(item => {
            const id = parseInt(item.getAttribute('data-id'));
            const text = item.querySelector('input[data-field="text"]').value.trim();
            const icon = item.querySelector('.ai-command-item-icon i').className.split(' ').filter(c => c.startsWith('fa-')).join(' ');
            const category = item.querySelector('.ai-command-category').textContent;
            
            if (text) {
                commands.push({ id, text, icon, category });
            }
        });
        
        // 保存并刷新
        this.saveCommands(commands);
        this.renderQuickCommands(commands);
        this.closeCommandEditor();
        this.showToast('快捷命令已保存', 'success');
    }
    
    addNewCommand() {
        const commands = this.getStoredCommands() || this.getDefaultCommands();
        const newId = Math.max(...commands.map(c => c.id)) + 1;
        const newCommand = {
            id: newId,
            text: '新命令',
            icon: 'fa-plus',
            category: '通用'
        };
        
        commands.push(newCommand);
        
        // 重新渲染
        document.getElementById('commandEditorBody').innerHTML = this.renderCommandList(commands);
        
        // 聚焦到新命令的输入框
        const newInput = document.querySelector(`.ai-command-item[data-id="${newId}"] input`);
        if (newInput) {
            newInput.focus();
            newInput.select();
        }
    }
    
    deleteCommand(id) {
        if (!confirm('确定要删除这个快捷命令吗？')) {
            return;
        }
        
        let commands = this.getStoredCommands() || this.getDefaultCommands();
        commands = commands.filter(c => c.id !== id);
        
        // 重新渲染
        document.getElementById('commandEditorBody').innerHTML = this.renderCommandList(commands);
        this.showToast('命令已删除', 'info');
    }
    
    editCommandIcon(id) {
        const iconOptions = [
            'fa-calendar-day', 'fa-calendar-week', 'fa-clock', 'fa-star',
            'fa-envelope', 'fa-briefcase', 'fa-dollar-sign', 'fa-chart-bar',
            'fa-chart-pie', 'fa-filter', 'fa-search', 'fa-tag',
            'fa-user', 'fa-users', 'fa-inbox', 'fa-paper-plane',
            'fa-bell', 'fa-flag', 'fa-heart', 'fa-bookmark'
        ];
        
        const iconPickerHtml = `
            <div class="ai-icon-picker">
                ${iconOptions.map(icon => `
                    <button class="ai-icon-option" onclick="aiAssistant.selectIcon(${id}, '${icon}')">
                        <i class="fas ${icon}"></i>
                    </button>
                `).join('')}
            </div>
        `;
        
        const item = document.querySelector(`.ai-command-item[data-id="${id}"]`);
        const existingPicker = item.querySelector('.ai-icon-picker');
        if (existingPicker) {
            existingPicker.remove();
        } else {
            const content = item.querySelector('.ai-command-item-content');
            content.insertAdjacentHTML('afterend', iconPickerHtml);
        }
    }
    
    selectIcon(id, icon) {
        const item = document.querySelector(`.ai-command-item[data-id="${id}"]`);
        const iconElement = item.querySelector('.ai-command-item-icon i');
        iconElement.className = `fas ${icon}`;
        
        // 移除图标选择器
        const picker = item.querySelector('.ai-icon-picker');
        if (picker) {
            picker.remove();
        }
    }
    
    resetCommands() {
        if (!confirm('确定要恢复为默认快捷命令吗？这将删除所有自定义命令。')) {
            return;
        }
        
        const defaultCommands = this.getDefaultCommands();
        document.getElementById('commandEditorBody').innerHTML = this.renderCommandList(defaultCommands);
        this.showToast('已恢复为默认命令', 'info');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 全局实例
let aiAssistant;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    aiAssistant = new AIAssistant();
    console.log('AI助手已初始化');
});

