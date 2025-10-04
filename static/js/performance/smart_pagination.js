/*!
 * AI邮件简报系统 - 智能分页组件
 * 支持预加载、缓存和无限滚动
 */

class SmartPagination {
    constructor(options) {
        this.apiUrl = options.apiUrl;
        this.container = options.container;
        this.onDataReceived = options.onDataReceived;
        this.onError = options.onError;
        this.pageSize = options.pageSize || 20;
        this.preloadPages = options.preloadPages || 1; // 预加载页数
        this.maxCachePages = options.maxCachePages || 10; // 最大缓存页数
        
        // 状态管理
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalItems = 0;
        this.isLoading = false;
        this.hasMore = true;
        
        // 缓存管理
        this.pageCache = new Map();
        this.cacheTimestamps = new Map();
        this.cacheTimeout = options.cacheTimeout || 300000; // 5分钟缓存
        
        // 预加载队列
        this.preloadQueue = [];
        this.isPreloading = false;
        
        this.init();
    }
    
    init() {
        this.setupPaginationContainer();
        this.bindEvents();
    }
    
    setupPaginationContainer() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <nav aria-label="智能分页导航" class="smart-pagination">
                <div class="pagination-info d-flex justify-content-between align-items-center mb-3">
                    <div class="pagination-stats">
                        <span class="text-muted">
                            显示第 <span class="current-start">0</span> - <span class="current-end">0</span> 项，
                            共 <span class="total-items">0</span> 项
                        </span>
                    </div>
                    <div class="pagination-controls">
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-secondary btn-first" disabled>
                                <i class="fas fa-angle-double-left"></i> 首页
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-prev" disabled>
                                <i class="fas fa-angle-left"></i> 上一页
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-next" disabled>
                                下一页 <i class="fas fa-angle-right"></i>
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-last" disabled>
                                末页 <i class="fas fa-angle-double-right"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="pagination-pages">
                    <ul class="pagination pagination-sm justify-content-center mb-0">
                        <!-- 页码按钮将动态生成 -->
                    </ul>
                </div>
                <div class="pagination-loading text-center mt-3" style="display: none;">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    <span>正在加载...</span>
                </div>
                <div class="pagination-cache-info text-center mt-2" style="display: none;">
                    <small class="text-muted">
                        <i class="fas fa-memory me-1"></i>
                        已缓存 <span class="cached-pages">0</span> 页数据
                    </small>
                </div>
            </nav>
        `;
        
        // 获取DOM元素引用
        this.elements = {
            currentStart: this.container.querySelector('.current-start'),
            currentEnd: this.container.querySelector('.current-end'),
            totalItems: this.container.querySelector('.total-items'),
            btnFirst: this.container.querySelector('.btn-first'),
            btnPrev: this.container.querySelector('.btn-prev'),
            btnNext: this.container.querySelector('.btn-next'),
            btnLast: this.container.querySelector('.btn-last'),
            paginationPages: this.container.querySelector('.pagination-pages ul'),
            loadingEl: this.container.querySelector('.pagination-loading'),
            cacheInfo: this.container.querySelector('.pagination-cache-info'),
            cachedPages: this.container.querySelector('.cached-pages')
        };
    }
    
    bindEvents() {
        if (!this.container) return;
        
        // 分页按钮事件
        this.elements.btnFirst.addEventListener('click', () => this.goToPage(1));
        this.elements.btnPrev.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        this.elements.btnNext.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        this.elements.btnLast.addEventListener('click', () => this.goToPage(this.totalPages));
        
        // 页码按钮事件（事件委托）
        this.elements.paginationPages.addEventListener('click', (e) => {
            if (e.target.classList.contains('page-link')) {
                e.preventDefault();
                const page = parseInt(e.target.dataset.page);
                if (page && !isNaN(page)) {
                    this.goToPage(page);
                }
            }
        });
    }
    
    async loadPage(page, useCache = true) {
        if (this.isLoading) return null;
        
        // 检查缓存
        if (useCache && this.isCacheValid(page)) {
            const cachedData = this.pageCache.get(page);
            this.updatePaginationInfo(cachedData);
            return cachedData;
        }
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const url = new URL(this.apiUrl);
            url.searchParams.set('page', page);
            url.searchParams.set('per_page', this.pageSize);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // 更新状态
            this.currentPage = page;
            this.totalPages = data.pagination?.pages || Math.ceil(data.total / this.pageSize);
            this.totalItems = data.total || 0;
            this.hasMore = page < this.totalPages;
            
            // 缓存数据
            this.cachePageData(page, data);
            
            // 更新UI
            this.updatePaginationInfo(data);
            this.updatePaginationButtons();
            this.updatePageNumbers();
            
            // 触发数据接收回调
            if (this.onDataReceived) {
                this.onDataReceived(data, page);
            }
            
            // 启动预加载
            this.startPreloading();
            
            return data;
            
        } catch (error) {
            console.error('分页加载失败:', error);
            if (this.onError) {
                this.onError(error, page);
            }
            return null;
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    async goToPage(page) {
        if (page < 1 || page > this.totalPages || page === this.currentPage) {
            return;
        }
        
        const data = await this.loadPage(page);
        return data;
    }
    
    async nextPage() {
        return this.goToPage(this.currentPage + 1);
    }
    
    async prevPage() {
        return this.goToPage(this.currentPage - 1);
    }
    
    async firstPage() {
        return this.goToPage(1);
    }
    
    async lastPage() {
        return this.goToPage(this.totalPages);
    }
    
    // 缓存管理
    cachePageData(page, data) {
        // 清理过期缓存
        this.cleanExpiredCache();
        
        // 限制缓存大小
        if (this.pageCache.size >= this.maxCachePages) {
            const oldestPage = Math.min(...this.pageCache.keys());
            this.pageCache.delete(oldestPage);
            this.cacheTimestamps.delete(oldestPage);
        }
        
        // 添加新缓存
        this.pageCache.set(page, data);
        this.cacheTimestamps.set(page, Date.now());
        
        // 更新缓存信息显示
        this.updateCacheInfo();
    }
    
    isCacheValid(page) {
        if (!this.pageCache.has(page)) return false;
        
        const timestamp = this.cacheTimestamps.get(page);
        const now = Date.now();
        
        return (now - timestamp) < this.cacheTimeout;
    }
    
    cleanExpiredCache() {
        const now = Date.now();
        
        for (const [page, timestamp] of this.cacheTimestamps.entries()) {
            if (now - timestamp >= this.cacheTimeout) {
                this.pageCache.delete(page);
                this.cacheTimestamps.delete(page);
            }
        }
    }
    
    clearCache() {
        this.pageCache.clear();
        this.cacheTimestamps.clear();
        this.updateCacheInfo();
    }
    
    // 预加载机制
    startPreloading() {
        if (this.isPreloading || this.preloadPages <= 0) return;
        
        // 构建预加载队列
        this.preloadQueue = [];
        
        // 预加载后续页面
        for (let i = 1; i <= this.preloadPages; i++) {
            const nextPage = this.currentPage + i;
            if (nextPage <= this.totalPages && !this.isCacheValid(nextPage)) {
                this.preloadQueue.push(nextPage);
            }
        }
        
        // 预加载前面的页面
        for (let i = 1; i <= this.preloadPages; i++) {
            const prevPage = this.currentPage - i;
            if (prevPage >= 1 && !this.isCacheValid(prevPage)) {
                this.preloadQueue.push(prevPage);
            }
        }
        
        // 开始预加载
        this.processPreloadQueue();
    }
    
    async processPreloadQueue() {
        if (this.isPreloading || this.preloadQueue.length === 0) return;
        
        this.isPreloading = true;
        
        while (this.preloadQueue.length > 0) {
            const page = this.preloadQueue.shift();
            
            try {
                // 延迟预加载，避免影响用户操作
                await this.delay(500);
                
                // 静默加载（不显示loading，不触发回调）
                await this.silentLoadPage(page);
                
            } catch (error) {
                console.warn(`预加载页面 ${page} 失败:`, error);
            }
        }
        
        this.isPreloading = false;
    }
    
    async silentLoadPage(page) {
        try {
            const url = new URL(this.apiUrl);
            url.searchParams.set('page', page);
            url.searchParams.set('per_page', this.pageSize);
            
            const response = await fetch(url);
            if (!response.ok) return;
            
            const data = await response.json();
            this.cachePageData(page, data);
            
        } catch (error) {
            // 静默失败
        }
    }
    
    // UI更新方法
    updatePaginationInfo(data) {
        if (!this.elements) return;
        
        const start = (this.currentPage - 1) * this.pageSize + 1;
        const end = Math.min(start + this.pageSize - 1, this.totalItems);
        
        this.elements.currentStart.textContent = this.totalItems > 0 ? start : 0;
        this.elements.currentEnd.textContent = this.totalItems > 0 ? end : 0;
        this.elements.totalItems.textContent = this.totalItems;
    }
    
    updatePaginationButtons() {
        if (!this.elements) return;
        
        this.elements.btnFirst.disabled = this.currentPage <= 1;
        this.elements.btnPrev.disabled = this.currentPage <= 1;
        this.elements.btnNext.disabled = this.currentPage >= this.totalPages;
        this.elements.btnLast.disabled = this.currentPage >= this.totalPages;
    }
    
    updatePageNumbers() {
        if (!this.elements) return;
        
        const maxVisible = 7; // 最多显示7个页码
        const half = Math.floor(maxVisible / 2);
        
        let startPage = Math.max(1, this.currentPage - half);
        let endPage = Math.min(this.totalPages, startPage + maxVisible - 1);
        
        // 调整起始页
        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }
        
        let html = '';
        
        // 第一页和省略号
        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        // 页码按钮
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === this.currentPage;
            const isCached = this.isCacheValid(i);
            const cacheClass = isCached ? 'cached' : '';
            
            html += `
                <li class="page-item ${isActive ? 'active' : ''} ${cacheClass}">
                    <a class="page-link" href="#" data-page="${i}">
                        ${i}
                        ${isCached ? '<small><i class="fas fa-memory"></i></small>' : ''}
                    </a>
                </li>
            `;
        }
        
        // 最后一页和省略号
        if (endPage < this.totalPages) {
            if (endPage < this.totalPages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${this.totalPages}">${this.totalPages}</a></li>`;
        }
        
        this.elements.paginationPages.innerHTML = html;
    }
    
    updateCacheInfo() {
        if (!this.elements) return;
        
        const cachedCount = this.pageCache.size;
        this.elements.cachedPages.textContent = cachedCount;
        
        if (cachedCount > 0) {
            this.elements.cacheInfo.style.display = 'block';
        } else {
            this.elements.cacheInfo.style.display = 'none';
        }
    }
    
    showLoading() {
        if (this.elements.loadingEl) {
            this.elements.loadingEl.style.display = 'block';
        }
    }
    
    hideLoading() {
        if (this.elements.loadingEl) {
            this.elements.loadingEl.style.display = 'none';
        }
    }
    
    // 工具方法
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // 获取状态信息
    getState() {
        return {
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            totalItems: this.totalItems,
            pageSize: this.pageSize,
            isLoading: this.isLoading,
            hasMore: this.hasMore,
            cachedPages: this.pageCache.size,
            preloadQueueSize: this.preloadQueue.length,
            isPreloading: this.isPreloading
        };
    }
    
    // 配置更新
    updateConfig(newConfig) {
        if (newConfig.pageSize) this.pageSize = newConfig.pageSize;
        if (newConfig.preloadPages !== undefined) this.preloadPages = newConfig.preloadPages;
        if (newConfig.maxCachePages) this.maxCachePages = newConfig.maxCachePages;
        if (newConfig.cacheTimeout) this.cacheTimeout = newConfig.cacheTimeout;
    }
    
    // 销毁方法
    destroy() {
        this.clearCache();
        this.preloadQueue = [];
        
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        // 清空引用
        this.elements = null;
        this.onDataReceived = null;
        this.onError = null;
    }
}

// 无限滚动分页类
class InfiniteScrollPagination extends SmartPagination {
    constructor(options) {
        super(options);
        
        this.scrollContainer = options.scrollContainer || window;
        this.loadMoreThreshold = options.loadMoreThreshold || 200; // 距离底部200px时加载
        this.autoLoad = options.autoLoad !== false; // 默认自动加载
        
        this.bindScrollEvents();
    }
    
    bindScrollEvents() {
        if (!this.autoLoad) return;
        
        const scrollHandler = this.throttle(() => {
            this.checkLoadMore();
        }, 100);
        
        if (this.scrollContainer === window) {
            window.addEventListener('scroll', scrollHandler);
        } else {
            this.scrollContainer.addEventListener('scroll', scrollHandler);
        }
        
        this.scrollHandler = scrollHandler;
    }
    
    checkLoadMore() {
        if (this.isLoading || !this.hasMore) return;
        
        let scrollTop, scrollHeight, clientHeight;
        
        if (this.scrollContainer === window) {
            scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            scrollHeight = document.documentElement.scrollHeight;
            clientHeight = window.innerHeight;
        } else {
            scrollTop = this.scrollContainer.scrollTop;
            scrollHeight = this.scrollContainer.scrollHeight;
            clientHeight = this.scrollContainer.clientHeight;
        }
        
        const distanceToBottom = scrollHeight - (scrollTop + clientHeight);
        
        if (distanceToBottom <= this.loadMoreThreshold) {
            this.loadMore();
        }
    }
    
    async loadMore() {
        if (!this.hasMore || this.isLoading) return;
        
        const nextPage = this.currentPage + 1;
        const data = await this.loadPage(nextPage);
        
        return data;
    }
    
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
    
    destroy() {
        // 移除滚动事件监听器
        if (this.scrollHandler) {
            if (this.scrollContainer === window) {
                window.removeEventListener('scroll', this.scrollHandler);
            } else {
                this.scrollContainer.removeEventListener('scroll', this.scrollHandler);
            }
        }
        
        super.destroy();
    }
}

// 导出类
window.SmartPagination = SmartPagination;
window.InfiniteScrollPagination = InfiniteScrollPagination;
