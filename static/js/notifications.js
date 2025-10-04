/**
 * ============================================================
 * 通知系统 JavaScript
 * ============================================================
 */

class NotificationSystem {
    constructor() {
        this.unreadCount = 0;
        this.notifications = [];
        this.isOpen = false;
        this.updateInterval = null;
        this.toastContainer = null;
        
        this.init();
    }
    
    /**
     * 初始化通知系统
     */
    init() {
        this.createToastContainer();
        this.createNotificationBell();
        this.startAutoUpdate();
        
        // 页面加载时立即更新一次
        this.updateUnreadCount();
        
        // 点击页面其他地方关闭通知面板
        document.addEventListener('click', (e) => {
            const bell = document.querySelector('.notification-bell');
            const dropdown = document.querySelector('.notification-dropdown');
            
            if (bell && dropdown && !bell.contains(e.target) && !dropdown.contains(e.target)) {
                this.closeDropdown();
            }
        });
    }
    
    /**
     * 创建Toast容器
     */
    createToastContainer() {
        this.toastContainer = document.createElement('div');
        this.toastContainer.className = 'toast-container';
        document.body.appendChild(this.toastContainer);
    }
    
    /**
     * 创建通知铃铛
     */
    createNotificationBell() {
        const navbarNav = document.querySelector('.navbar-nav');
        if (!navbarNav) return;
        
        // 找到"实时收取"按钮的父元素
        const triggerBtnLi = document.querySelector('#trigger-btn')?.closest('li');
        if (!triggerBtnLi) return;
        
        // 创建通知铃铛元素
        const bellLi = document.createElement('li');
        bellLi.className = 'nav-item position-relative';
        bellLi.innerHTML = `
            <div class="notification-bell" id="notification-bell">
                <i class="fas fa-bell bell-icon"></i>
                <span class="notification-badge" id="notification-badge" style="display: none;">0</span>
            </div>
        `;
        
        // 插入到"实时收取"按钮后面
        triggerBtnLi.parentNode.insertBefore(bellLi, triggerBtnLi.nextSibling);
        
        // 创建下拉面板
        const dropdown = document.createElement('div');
        dropdown.className = 'notification-dropdown';
        dropdown.id = 'notification-dropdown';
        dropdown.innerHTML = `
            <div class="notification-header">
                <h6><i class="fas fa-bell me-2"></i>系统通知</h6>
                <div class="notification-header-actions">
                    <button onclick="notificationSystem.markAllAsRead()" title="全部标记为已读">
                        <i class="fas fa-check-double"></i>
                    </button>
                    <button onclick="notificationSystem.closeDropdown()" title="关闭">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="notification-list" id="notification-list">
                <div class="notification-loading">
                    <div class="notification-loading-spinner"></div>
                    <p class="mt-2 mb-0 text-muted">加载中...</p>
                </div>
            </div>
            <div class="notification-footer">
                <a href="#" onclick="notificationSystem.viewAllNotifications(); return false;">
                    查看全部通知
                </a>
            </div>
        `;
        
        bellLi.appendChild(dropdown);
        
        // 绑定点击事件
        document.getElementById('notification-bell').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });
    }
    
    /**
     * 开始自动更新
     */
    startAutoUpdate() {
        // 每30秒更新一次未读数量
        this.updateInterval = setInterval(() => {
            this.updateUnreadCount();
        }, 30000);
    }
    
    /**
     * 更新未读通知数量
     */
    async updateUnreadCount() {
        try {
            const response = await fetch('/api/notifications/unread-count');
            const data = await response.json();
            
            if (data.success) {
                this.unreadCount = data.count;
                this.updateBadge();
            }
        } catch (error) {
            console.error('更新未读数量失败:', error);
        }
    }
    
    /**
     * 更新徽章显示
     */
    updateBadge() {
        const badge = document.getElementById('notification-badge');
        if (!badge) return;
        
        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
    
    /**
     * 切换下拉面板
     */
    toggleDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (!dropdown) return;
        
        if (this.isOpen) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }
    
    /**
     * 打开下拉面板
     */
    async openDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (!dropdown) return;
        
        dropdown.classList.add('show');
        this.isOpen = true;
        
        // 加载通知列表
        await this.loadNotifications();
    }
    
    /**
     * 关闭下拉面板
     */
    closeDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (!dropdown) return;
        
        dropdown.classList.remove('show');
        this.isOpen = false;
    }
    
    /**
     * 加载通知列表
     */
    async loadNotifications(page = 1) {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;
        
        try {
            const response = await fetch(`/api/notifications?page=${page}&per_page=10`);
            const data = await response.json();
            
            if (data.success) {
                this.notifications = data.notifications;
                this.renderNotifications();
            } else {
                this.showEmptyState('加载失败，请稍后重试');
            }
        } catch (error) {
            console.error('加载通知失败:', error);
            this.showEmptyState('网络错误，无法加载通知');
        }
    }
    
    /**
     * 渲染通知列表
     */
    renderNotifications() {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;
        
        if (this.notifications.length === 0) {
            this.showEmptyState();
            return;
        }
        
        let html = '';
        this.notifications.forEach(notif => {
            const iconClass = this.getNotificationIcon(notif.type);
            const isUnread = !notif.is_read;
            
            html += `
                <div class="notification-item ${isUnread ? 'unread' : ''}" data-id="${notif.id}">
                    <div class="d-flex align-items-start">
                        <div class="notification-icon ${notif.type}">
                            <i class="fas ${iconClass}"></i>
                        </div>
                        <div class="notification-content">
                            <div class="notification-title">${this.escapeHtml(notif.title)}</div>
                            <div class="notification-message">${this.escapeHtml(notif.message)}</div>
                            <span class="notification-time">${this.formatTime(notif.created_at)}</span>
                            ${isUnread ? `
                                <div class="notification-actions">
                                    <button class="btn-mark-read" onclick="notificationSystem.markAsRead(${notif.id})">
                                        <i class="fas fa-check me-1"></i>标记已读
                                    </button>
                                    <button class="btn-delete" onclick="notificationSystem.deleteNotification(${notif.id})">
                                        <i class="fas fa-trash me-1"></i>删除
                                    </button>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        listContainer.innerHTML = html;
    }
    
    /**
     * 显示空状态
     */
    showEmptyState(message = '暂无通知') {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;
        
        listContainer.innerHTML = `
            <div class="notification-empty">
                <div class="notification-empty-icon">
                    <i class="fas fa-bell-slash"></i>
                </div>
                <div class="notification-empty-text">${message}</div>
            </div>
        `;
    }
    
    /**
     * 标记单条通知为已读
     */
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/read`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 更新本地状态
                const notif = this.notifications.find(n => n.id === notificationId);
                if (notif) {
                    notif.is_read = true;
                }
                
                // 重新渲染
                this.renderNotifications();
                
                // 更新未读数量
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('标记已读失败:', error);
            this.showToast('error', '操作失败', '标记已读失败，请稍后重试');
        }
    }
    
    /**
     * 标记所有通知为已读
     */
    async markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/mark-all-read', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 更新本地状态
                this.notifications.forEach(notif => {
                    notif.is_read = true;
                });
                
                // 重新渲染
                this.renderNotifications();
                
                // 更新未读数量
                this.unreadCount = 0;
                this.updateBadge();
                
                this.showToast('success', '操作成功', '所有通知已标记为已读');
            }
        } catch (error) {
            console.error('标记所有已读失败:', error);
            this.showToast('error', '操作失败', '标记失败，请稍后重试');
        }
    }
    
    /**
     * 删除通知
     */
    async deleteNotification(notificationId) {
        if (!confirm('确定要删除这条通知吗？')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/notifications/${notificationId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 从本地列表中移除
                this.notifications = this.notifications.filter(n => n.id !== notificationId);
                
                // 重新渲染
                this.renderNotifications();
                
                // 更新未读数量
                this.updateUnreadCount();
                
                this.showToast('success', '删除成功', '通知已删除');
            }
        } catch (error) {
            console.error('删除通知失败:', error);
            this.showToast('error', '删除失败', '无法删除通知，请稍后重试');
        }
    }
    
    /**
     * 查看所有通知（跳转到通知中心页面）
     */
    viewAllNotifications() {
        window.location.href = '/notifications';
    }
    
    /**
     * 显示Toast通知
     */
    showToast(type, title, message, duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        
        const iconClass = this.getNotificationIcon(type);
        
        toast.innerHTML = `
            <div class="toast-header">
                <span class="toast-header-icon">
                    <i class="fas ${iconClass}"></i>
                </span>
                <span class="toast-header-title">${this.escapeHtml(title)}</span>
                <button class="toast-close" onclick="this.closest('.toast-notification').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="toast-body">
                ${this.escapeHtml(message)}
            </div>
            <div class="toast-progress">
                <div class="toast-progress-bar"></div>
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // 自动关闭
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    /**
     * 检查最新通知（用于邮件收取后）
     */
    async checkForNewNotifications() {
        try {
            const response = await fetch('/api/notifications?page=1&per_page=1');
            const data = await response.json();
            
            if (data.success && data.notifications.length > 0) {
                const latest = data.notifications[0];
                
                // 显示Toast通知
                this.showToast(
                    latest.type,
                    latest.title,
                    latest.message,
                    5000
                );
                
                // 更新未读数量
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('检查新通知失败:', error);
        }
    }
    
    /**
     * 获取通知图标
     */
    getNotificationIcon(type) {
        const icons = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle'
        };
        
        return icons[type] || 'fa-bell';
    }
    
    /**
     * 格式化时间
     */
    formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) {
            return '刚刚';
        } else if (diffMins < 60) {
            return `${diffMins}分钟前`;
        } else if (diffHours < 24) {
            return `${diffHours}小时前`;
        } else if (diffDays < 7) {
            return `${diffDays}天前`;
        } else {
            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }
    
    /**
     * HTML转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 销毁通知系统
     */
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.toastContainer) {
            this.toastContainer.remove();
        }
    }
}

// 全局通知系统实例
let notificationSystem;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 只在已登录状态下初始化通知系统
    if (document.getElementById('trigger-btn')) {
        notificationSystem = new NotificationSystem();
    }
});

// 增强原有的邮件收取函数
if (typeof triggerProcessing !== 'undefined') {
    const originalTriggerProcessing = triggerProcessing;
    
    triggerProcessing = function() {
        originalTriggerProcessing();
        
        // 邮件收取完成后检查新通知
        setTimeout(() => {
            if (notificationSystem) {
                notificationSystem.checkForNewNotifications();
            }
        }, 5000);
    };
}

