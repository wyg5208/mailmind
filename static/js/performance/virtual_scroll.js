/*!
 * AI邮件简报系统 - 虚拟滚动组件
 * 用于优化大量邮件列表的渲染性能
 */

class VirtualScrollList {
    constructor(options) {
        this.container = options.container;
        this.itemHeight = options.itemHeight || 80;
        this.buffer = options.buffer || 5; // 缓冲区项目数
        this.data = options.data || [];
        this.renderItem = options.renderItem;
        this.onLoadMore = options.onLoadMore;
        this.loadMoreThreshold = options.loadMoreThreshold || 10;
        
        // 状态变量
        this.scrollTop = 0;
        this.containerHeight = 0;
        this.visibleStart = 0;
        this.visibleEnd = 0;
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.setupContainer();
        this.bindEvents();
        this.update();
    }
    
    setupContainer() {
        // 创建虚拟滚动容器结构
        this.container.innerHTML = `
            <div class="virtual-scroll-wrapper" style="overflow-y: auto; height: 100%;">
                <div class="virtual-scroll-spacer-top" style="height: 0px;"></div>
                <div class="virtual-scroll-content"></div>
                <div class="virtual-scroll-spacer-bottom" style="height: 0px;"></div>
                <div class="virtual-scroll-loading" style="display: none; text-align: center; padding: 20px;">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    正在加载更多...
                </div>
            </div>
        `;
        
        this.wrapper = this.container.querySelector('.virtual-scroll-wrapper');
        this.spacerTop = this.container.querySelector('.virtual-scroll-spacer-top');
        this.content = this.container.querySelector('.virtual-scroll-content');
        this.spacerBottom = this.container.querySelector('.virtual-scroll-spacer-bottom');
        this.loadingEl = this.container.querySelector('.virtual-scroll-loading');
        
        this.containerHeight = this.wrapper.clientHeight;
    }
    
    bindEvents() {
        // 滚动事件
        this.wrapper.addEventListener('scroll', this.throttle(() => {
            this.scrollTop = this.wrapper.scrollTop;
            this.update();
            this.checkLoadMore();
        }, 16)); // 60fps
        
        // 窗口大小变化事件
        window.addEventListener('resize', this.throttle(() => {
            this.containerHeight = this.wrapper.clientHeight;
            this.update();
        }, 100));
    }
    
    update() {
        if (!this.data.length) {
            this.content.innerHTML = '<div class="text-center text-muted py-4">暂无数据</div>';
            return;
        }
        
        // 计算可见范围
        const visibleCount = Math.ceil(this.containerHeight / this.itemHeight);
        this.visibleStart = Math.max(0, Math.floor(this.scrollTop / this.itemHeight) - this.buffer);
        this.visibleEnd = Math.min(this.data.length, this.visibleStart + visibleCount + this.buffer * 2);
        
        // 更新spacer高度
        this.spacerTop.style.height = `${this.visibleStart * this.itemHeight}px`;
        this.spacerBottom.style.height = `${(this.data.length - this.visibleEnd) * this.itemHeight}px`;
        
        // 渲染可见项目
        this.renderVisibleItems();
    }
    
    renderVisibleItems() {
        const fragment = document.createDocumentFragment();
        
        for (let i = this.visibleStart; i < this.visibleEnd; i++) {
            const item = this.data[i];
            if (!item) continue;
            
            const itemEl = this.createItemElement(item, i);
            fragment.appendChild(itemEl);
        }
        
        this.content.innerHTML = '';
        this.content.appendChild(fragment);
    }
    
    createItemElement(item, index) {
        const div = document.createElement('div');
        div.className = 'virtual-scroll-item';
        div.style.height = `${this.itemHeight}px`;
        div.dataset.index = index;
        
        if (this.renderItem) {
            div.innerHTML = this.renderItem(item, index);
        } else {
            div.innerHTML = `<div class="p-3">Item ${index}: ${JSON.stringify(item)}</div>`;
        }
        
        return div;
    }
    
    checkLoadMore() {
        if (this.isLoading || !this.onLoadMore) return;
        
        // 检查是否接近底部
        const scrollBottom = this.scrollTop + this.containerHeight;
        const totalHeight = this.data.length * this.itemHeight;
        const threshold = totalHeight - (this.loadMoreThreshold * this.itemHeight);
        
        if (scrollBottom >= threshold) {
            this.loadMore();
        }
    }
    
    async loadMore() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const newData = await this.onLoadMore();
            if (newData && newData.length > 0) {
                this.appendData(newData);
            }
        } catch (error) {
            console.error('加载更多数据失败:', error);
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    showLoading() {
        this.loadingEl.style.display = 'block';
    }
    
    hideLoading() {
        this.loadingEl.style.display = 'none';
    }
    
    // 数据操作方法
    setData(newData) {
        this.data = newData || [];
        this.scrollTop = 0;
        this.wrapper.scrollTop = 0;
        this.update();
    }
    
    appendData(newData) {
        if (!newData || !newData.length) return;
        
        this.data.push(...newData);
        this.update();
    }
    
    prependData(newData) {
        if (!newData || !newData.length) return;
        
        const oldScrollTop = this.scrollTop;
        const addedHeight = newData.length * this.itemHeight;
        
        this.data.unshift(...newData);
        this.update();
        
        // 保持滚动位置
        this.wrapper.scrollTop = oldScrollTop + addedHeight;
    }
    
    removeItem(index) {
        if (index >= 0 && index < this.data.length) {
            this.data.splice(index, 1);
            this.update();
        }
    }
    
    updateItem(index, newItem) {
        if (index >= 0 && index < this.data.length) {
            this.data[index] = newItem;
            this.update();
        }
    }
    
    // 滚动控制方法
    scrollToIndex(index) {
        if (index >= 0 && index < this.data.length) {
            const targetScrollTop = index * this.itemHeight;
            this.wrapper.scrollTop = targetScrollTop;
        }
    }
    
    scrollToTop() {
        this.wrapper.scrollTop = 0;
    }
    
    scrollToBottom() {
        this.wrapper.scrollTop = this.data.length * this.itemHeight;
    }
    
    // 工具方法
    throttle(func, delay) {
        let timeoutId;
        let lastExecTime = 0;
        
        return function (...args) {
            const currentTime = Date.now();
            
            if (currentTime - lastExecTime > delay) {
                func.apply(this, args);
                lastExecTime = currentTime;
            } else {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => {
                    func.apply(this, args);
                    lastExecTime = Date.now();
                }, delay - (currentTime - lastExecTime));
            }
        };
    }
    
    // 获取状态信息
    getState() {
        return {
            totalItems: this.data.length,
            visibleStart: this.visibleStart,
            visibleEnd: this.visibleEnd,
            visibleCount: this.visibleEnd - this.visibleStart,
            scrollTop: this.scrollTop,
            containerHeight: this.containerHeight,
            isLoading: this.isLoading
        };
    }
    
    // 销毁方法
    destroy() {
        // 移除事件监听器
        this.wrapper.removeEventListener('scroll', this.update);
        window.removeEventListener('resize', this.update);
        
        // 清空容器
        this.container.innerHTML = '';
        
        // 清空引用
        this.data = null;
        this.renderItem = null;
        this.onLoadMore = null;
    }
}

// 邮件列表专用虚拟滚动类
class EmailVirtualList extends VirtualScrollList {
    constructor(options) {
        super({
            ...options,
            itemHeight: options.itemHeight || 120, // 邮件项目高度
            renderItem: options.renderItem || EmailVirtualList.defaultRenderItem
        });
        
        this.onEmailClick = options.onEmailClick;
        this.onEmailDelete = options.onEmailDelete;
        
        this.bindEmailEvents();
    }
    
    static defaultRenderItem(email, index) {
        const date = new Date(email.date).toLocaleString('zh-CN');
        const processedBadge = email.processed 
            ? '<span class="badge bg-success">已处理</span>'
            : '<span class="badge bg-warning">未处理</span>';
        
        return `
            <div class="email-item p-3 border-bottom" data-email-id="${email.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 me-3">
                        <h6 class="mb-1 email-subject" title="${email.subject}">
                            ${email.subject || '无主题'}
                        </h6>
                        <div class="text-muted small mb-1">
                            <i class="fas fa-user me-1"></i>
                            <span class="email-sender">${email.sender || '未知发送者'}</span>
                            <span class="mx-2">•</span>
                            <i class="fas fa-clock me-1"></i>
                            <span class="email-date">${date}</span>
                        </div>
                        ${email.ai_summary ? `
                            <div class="email-summary text-muted small">
                                <i class="fas fa-robot me-1"></i>
                                ${email.ai_summary.substring(0, 100)}${email.ai_summary.length > 100 ? '...' : ''}
                            </div>
                        ` : ''}
                    </div>
                    <div class="d-flex flex-column align-items-end">
                        ${processedBadge}
                        <div class="btn-group btn-group-sm mt-2" role="group">
                            <button type="button" class="btn btn-outline-primary btn-view" 
                                    data-email-id="${email.id}" title="查看详情">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete" 
                                    data-email-id="${email.id}" title="删除">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    bindEmailEvents() {
        // 使用事件委托处理邮件操作
        this.content.addEventListener('click', (e) => {
            const emailId = e.target.closest('[data-email-id]')?.dataset.emailId;
            if (!emailId) return;
            
            if (e.target.closest('.btn-view')) {
                this.handleEmailClick(parseInt(emailId));
            } else if (e.target.closest('.btn-delete')) {
                this.handleEmailDelete(parseInt(emailId));
            } else if (e.target.closest('.email-item')) {
                this.handleEmailClick(parseInt(emailId));
            }
        });
    }
    
    handleEmailClick(emailId) {
        if (this.onEmailClick) {
            const email = this.data.find(e => e.id === emailId);
            this.onEmailClick(email, emailId);
        }
    }
    
    handleEmailDelete(emailId) {
        if (this.onEmailDelete) {
            const email = this.data.find(e => e.id === emailId);
            this.onEmailDelete(email, emailId);
        }
    }
    
    // 邮件特定方法
    markAsProcessed(emailId) {
        const index = this.data.findIndex(e => e.id === emailId);
        if (index !== -1) {
            this.data[index].processed = true;
            this.update();
        }
    }
    
    removeEmail(emailId) {
        const index = this.data.findIndex(e => e.id === emailId);
        if (index !== -1) {
            this.removeItem(index);
        }
    }
    
    addNewEmail(email) {
        this.prependData([email]);
    }
    
    updateEmailSummary(emailId, summary) {
        const index = this.data.findIndex(e => e.id === emailId);
        if (index !== -1) {
            this.data[index].ai_summary = summary;
            this.data[index].processed = true;
            this.update();
        }
    }
}

// 导出类
window.VirtualScrollList = VirtualScrollList;
window.EmailVirtualList = EmailVirtualList;
