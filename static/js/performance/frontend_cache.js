/*!
 * AI邮件简报系统 - 前端缓存管理器
 * 提供内存缓存、本地存储缓存和会话缓存功能
 */

class FrontendCacheManager {
    constructor(options = {}) {
        this.prefix = options.prefix || 'email_system_';
        this.defaultTTL = options.defaultTTL || 300000; // 5分钟
        this.maxMemoryItems = options.maxMemoryItems || 100;
        this.maxStorageSize = options.maxStorageSize || 10 * 1024 * 1024; // 10MB
        
        // 内存缓存
        this.memoryCache = new Map();
        this.memoryTimestamps = new Map();
        
        // 缓存统计
        this.stats = {
            hits: 0,
            misses: 0,
            sets: 0,
            deletes: 0,
            clears: 0
        };
        
        this.init();
    }
    
    init() {
        // 清理过期的localStorage数据
        this.cleanExpiredStorage();
        
        // 监听存储变化
        window.addEventListener('storage', (e) => {
            if (e.key && e.key.startsWith(this.prefix)) {
                this.handleStorageChange(e);
            }
        });
        
        // 页面卸载时清理内存缓存
        window.addEventListener('beforeunload', () => {
            this.clearMemoryCache();
        });
    }
    
    // ==================== 内存缓存 ====================
    
    setMemoryCache(key, data, ttl = this.defaultTTL) {
        try {
            // 限制内存缓存大小
            if (this.memoryCache.size >= this.maxMemoryItems) {
                this.evictOldestMemoryCache();
            }
            
            this.memoryCache.set(key, data);
            this.memoryTimestamps.set(key, Date.now() + ttl);
            this.stats.sets++;
            
            return true;
        } catch (error) {
            console.warn('内存缓存设置失败:', error);
            return false;
        }
    }
    
    getMemoryCache(key) {
        try {
            if (!this.memoryCache.has(key)) {
                this.stats.misses++;
                return null;
            }
            
            const timestamp = this.memoryTimestamps.get(key);
            if (Date.now() > timestamp) {
                // 过期，删除
                this.memoryCache.delete(key);
                this.memoryTimestamps.delete(key);
                this.stats.misses++;
                return null;
            }
            
            this.stats.hits++;
            return this.memoryCache.get(key);
        } catch (error) {
            console.warn('内存缓存获取失败:', error);
            this.stats.misses++;
            return null;
        }
    }
    
    deleteMemoryCache(key) {
        const deleted = this.memoryCache.delete(key);
        this.memoryTimestamps.delete(key);
        if (deleted) this.stats.deletes++;
        return deleted;
    }
    
    clearMemoryCache() {
        const size = this.memoryCache.size;
        this.memoryCache.clear();
        this.memoryTimestamps.clear();
        if (size > 0) this.stats.clears++;
        return size;
    }
    
    evictOldestMemoryCache() {
        // 删除最旧的缓存项
        let oldestKey = null;
        let oldestTime = Infinity;
        
        for (const [key, timestamp] of this.memoryTimestamps.entries()) {
            if (timestamp < oldestTime) {
                oldestTime = timestamp;
                oldestKey = key;
            }
        }
        
        if (oldestKey) {
            this.deleteMemoryCache(oldestKey);
        }
    }
    
    // ==================== 本地存储缓存 ====================
    
    setLocalCache(key, data, ttl = this.defaultTTL) {
        try {
            const storageKey = this.prefix + key;
            const cacheData = {
                data: data,
                timestamp: Date.now(),
                expires: Date.now() + ttl,
                size: JSON.stringify(data).length
            };
            
            // 检查存储空间
            if (!this.checkStorageSpace(cacheData.size)) {
                this.cleanOldestStorage();
            }
            
            localStorage.setItem(storageKey, JSON.stringify(cacheData));
            this.stats.sets++;
            
            return true;
        } catch (error) {
            console.warn('本地缓存设置失败:', error);
            return false;
        }
    }
    
    getLocalCache(key) {
        try {
            const storageKey = this.prefix + key;
            const cached = localStorage.getItem(storageKey);
            
            if (!cached) {
                this.stats.misses++;
                return null;
            }
            
            const cacheData = JSON.parse(cached);
            
            // 检查是否过期
            if (Date.now() > cacheData.expires) {
                localStorage.removeItem(storageKey);
                this.stats.misses++;
                return null;
            }
            
            this.stats.hits++;
            return cacheData.data;
        } catch (error) {
            console.warn('本地缓存获取失败:', error);
            this.stats.misses++;
            return null;
        }
    }
    
    deleteLocalCache(key) {
        try {
            const storageKey = this.prefix + key;
            const existed = localStorage.getItem(storageKey) !== null;
            localStorage.removeItem(storageKey);
            if (existed) this.stats.deletes++;
            return existed;
        } catch (error) {
            console.warn('本地缓存删除失败:', error);
            return false;
        }
    }
    
    clearLocalCache() {
        try {
            let count = 0;
            const keysToRemove = [];
            
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith(this.prefix)) {
                    keysToRemove.push(key);
                }
            }
            
            keysToRemove.forEach(key => {
                localStorage.removeItem(key);
                count++;
            });
            
            if (count > 0) this.stats.clears++;
            return count;
        } catch (error) {
            console.warn('本地缓存清理失败:', error);
            return 0;
        }
    }
    
    // ==================== 会话存储缓存 ====================
    
    setSessionCache(key, data, ttl = this.defaultTTL) {
        try {
            const storageKey = this.prefix + key;
            const cacheData = {
                data: data,
                timestamp: Date.now(),
                expires: Date.now() + ttl
            };
            
            sessionStorage.setItem(storageKey, JSON.stringify(cacheData));
            this.stats.sets++;
            
            return true;
        } catch (error) {
            console.warn('会话缓存设置失败:', error);
            return false;
        }
    }
    
    getSessionCache(key) {
        try {
            const storageKey = this.prefix + key;
            const cached = sessionStorage.getItem(storageKey);
            
            if (!cached) {
                this.stats.misses++;
                return null;
            }
            
            const cacheData = JSON.parse(cached);
            
            // 检查是否过期
            if (Date.now() > cacheData.expires) {
                sessionStorage.removeItem(storageKey);
                this.stats.misses++;
                return null;
            }
            
            this.stats.hits++;
            return cacheData.data;
        } catch (error) {
            console.warn('会话缓存获取失败:', error);
            this.stats.misses++;
            return null;
        }
    }
    
    deleteSessionCache(key) {
        try {
            const storageKey = this.prefix + key;
            const existed = sessionStorage.getItem(storageKey) !== null;
            sessionStorage.removeItem(storageKey);
            if (existed) this.stats.deletes++;
            return existed;
        } catch (error) {
            console.warn('会话缓存删除失败:', error);
            return false;
        }
    }
    
    clearSessionCache() {
        try {
            let count = 0;
            const keysToRemove = [];
            
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                if (key && key.startsWith(this.prefix)) {
                    keysToRemove.push(key);
                }
            }
            
            keysToRemove.forEach(key => {
                sessionStorage.removeItem(key);
                count++;
            });
            
            if (count > 0) this.stats.clears++;
            return count;
        } catch (error) {
            console.warn('会话缓存清理失败:', error);
            return 0;
        }
    }
    
    // ==================== 统一缓存接口 ====================
    
    set(key, data, options = {}) {
        const {
            type = 'memory', // memory, local, session, all
            ttl = this.defaultTTL
        } = options;
        
        let success = false;
        
        switch (type) {
            case 'memory':
                success = this.setMemoryCache(key, data, ttl);
                break;
            case 'local':
                success = this.setLocalCache(key, data, ttl);
                break;
            case 'session':
                success = this.setSessionCache(key, data, ttl);
                break;
            case 'all':
                const memSuccess = this.setMemoryCache(key, data, ttl);
                const localSuccess = this.setLocalCache(key, data, ttl);
                success = memSuccess || localSuccess;
                break;
        }
        
        return success;
    }
    
    get(key, options = {}) {
        const {
            type = 'auto' // auto, memory, local, session
        } = options;
        
        if (type === 'auto') {
            // 按优先级查找：内存 -> 会话 -> 本地
            let data = this.getMemoryCache(key);
            if (data !== null) return data;
            
            data = this.getSessionCache(key);
            if (data !== null) {
                // 回填到内存缓存
                this.setMemoryCache(key, data);
                return data;
            }
            
            data = this.getLocalCache(key);
            if (data !== null) {
                // 回填到内存和会话缓存
                this.setMemoryCache(key, data);
                this.setSessionCache(key, data);
                return data;
            }
            
            return null;
        }
        
        switch (type) {
            case 'memory':
                return this.getMemoryCache(key);
            case 'local':
                return this.getLocalCache(key);
            case 'session':
                return this.getSessionCache(key);
            default:
                return null;
        }
    }
    
    delete(key, options = {}) {
        const {
            type = 'all' // all, memory, local, session
        } = options;
        
        let deleted = false;
        
        if (type === 'all' || type === 'memory') {
            deleted = this.deleteMemoryCache(key) || deleted;
        }
        
        if (type === 'all' || type === 'local') {
            deleted = this.deleteLocalCache(key) || deleted;
        }
        
        if (type === 'all' || type === 'session') {
            deleted = this.deleteSessionCache(key) || deleted;
        }
        
        return deleted;
    }
    
    clear(options = {}) {
        const {
            type = 'all' // all, memory, local, session
        } = options;
        
        let totalCleared = 0;
        
        if (type === 'all' || type === 'memory') {
            totalCleared += this.clearMemoryCache();
        }
        
        if (type === 'all' || type === 'local') {
            totalCleared += this.clearLocalCache();
        }
        
        if (type === 'all' || type === 'session') {
            totalCleared += this.clearSessionCache();
        }
        
        return totalCleared;
    }
    
    // ==================== 工具方法 ====================
    
    checkStorageSpace(dataSize) {
        try {
            const currentSize = this.getStorageSize();
            return (currentSize + dataSize) <= this.maxStorageSize;
        } catch (error) {
            return false;
        }
    }
    
    getStorageSize() {
        let totalSize = 0;
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                const value = localStorage.getItem(key);
                totalSize += key.length + (value ? value.length : 0);
            }
        }
        
        return totalSize;
    }
    
    cleanOldestStorage() {
        const items = [];
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                try {
                    const value = localStorage.getItem(key);
                    const data = JSON.parse(value);
                    items.push({
                        key: key,
                        timestamp: data.timestamp || 0,
                        size: data.size || 0
                    });
                } catch (error) {
                    // 删除无效数据
                    localStorage.removeItem(key);
                }
            }
        }
        
        // 按时间戳排序，删除最旧的
        items.sort((a, b) => a.timestamp - b.timestamp);
        
        let freedSpace = 0;
        const targetSpace = this.maxStorageSize * 0.2; // 释放20%空间
        
        for (const item of items) {
            localStorage.removeItem(item.key);
            freedSpace += item.size;
            
            if (freedSpace >= targetSpace) break;
        }
    }
    
    cleanExpiredStorage() {
        const now = Date.now();
        const keysToRemove = [];
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                try {
                    const value = localStorage.getItem(key);
                    const data = JSON.parse(value);
                    
                    if (data.expires && now > data.expires) {
                        keysToRemove.push(key);
                    }
                } catch (error) {
                    // 删除无效数据
                    keysToRemove.push(key);
                }
            }
        }
        
        keysToRemove.forEach(key => localStorage.removeItem(key));
        return keysToRemove.length;
    }
    
    handleStorageChange(event) {
        // 处理其他标签页的存储变化
        if (event.newValue === null) {
            // 数据被删除，同步删除内存缓存
            const key = event.key.replace(this.prefix, '');
            this.deleteMemoryCache(key);
        }
    }
    
    // ==================== 统计和监控 ====================
    
    getStats() {
        const hitRate = this.stats.hits + this.stats.misses > 0 
            ? (this.stats.hits / (this.stats.hits + this.stats.misses) * 100).toFixed(2)
            : '0.00';
        
        return {
            ...this.stats,
            hitRate: `${hitRate}%`,
            memoryItems: this.memoryCache.size,
            localStorageSize: this.formatBytes(this.getStorageSize()),
            sessionItems: this.getSessionItemCount()
        };
    }
    
    getSessionItemCount() {
        let count = 0;
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                count++;
            }
        }
        return count;
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    resetStats() {
        this.stats = {
            hits: 0,
            misses: 0,
            sets: 0,
            deletes: 0,
            clears: 0
        };
    }
    
    // ==================== 调试方法 ====================
    
    debug() {
        console.group('前端缓存管理器状态');
        console.log('统计信息:', this.getStats());
        console.log('内存缓存键:', Array.from(this.memoryCache.keys()));
        console.log('本地存储键:', this.getLocalStorageKeys());
        console.log('会话存储键:', this.getSessionStorageKeys());
        console.groupEnd();
    }
    
    getLocalStorageKeys() {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                keys.push(key.replace(this.prefix, ''));
            }
        }
        return keys;
    }
    
    getSessionStorageKeys() {
        const keys = [];
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                keys.push(key.replace(this.prefix, ''));
            }
        }
        return keys;
    }
}

// 创建全局缓存管理器实例
window.frontendCache = new FrontendCacheManager({
    prefix: 'email_system_',
    defaultTTL: 300000, // 5分钟
    maxMemoryItems: 100,
    maxStorageSize: 10 * 1024 * 1024 // 10MB
});

// 导出类
window.FrontendCacheManager = FrontendCacheManager;
