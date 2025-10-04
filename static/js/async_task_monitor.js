/**
 * AI邮件简报系统 - 异步任务监控器类
 * 用于监控Celery任务的执行进度
 */

class AsyncTaskMonitor {
    /**
     * 构造函数
     * @param {string} taskId - Celery任务ID
     * @param {object} options - 配置选项
     */
    constructor(taskId, options = {}) {
        this.taskId = taskId;
        this.interval = options.interval || 1000; // 轮询间隔，默认1秒
        this.onProgress = options.onProgress || this._defaultOnProgress.bind(this);
        this.onSuccess = options.onSuccess || this._defaultOnSuccess.bind(this);
        this.onFailure = options.onFailure || this._defaultOnFailure.bind(this);
        this.onComplete = options.onComplete || this._defaultOnComplete.bind(this);
        this.pollingTimer = null;
        this.progressBarId = options.progressBarId || 'async-progress-bar';
        this.progressTextId = options.progressTextId || 'async-progress-text';
        this.progressContainerId = options.progressContainerId || 'async-progress-container';

        this._initUI();
    }

    /**
     * 初始化UI
     * @private
     */
    _initUI() {
        let container = document.getElementById(this.progressContainerId);
        if (!container) {
            container = document.createElement('div');
            container.id = this.progressContainerId;
            container.className = 'async-progress-container';
            container.innerHTML = `
                <div class="async-progress-bar-wrapper">
                    <div id="${this.progressBarId}" class="async-progress-bar" style="width: 0%;"></div>
                </div>
                <div id="${this.progressTextId}" class="async-progress-text">任务等待中...</div>
                <button id="async-progress-close" class="async-progress-close-btn" style="display:none;">×</button>
            `;
            document.body.appendChild(container);
            
            // 绑定关闭按钮事件
            const closeBtn = document.getElementById('async-progress-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.hide());
            }
        }
        this.hide(); // 默认隐藏
    }

    /**
     * 显示进度条
     */
    show() {
        const container = document.getElementById(this.progressContainerId);
        if (container) {
            container.style.display = 'flex';
        }
    }

    /**
     * 隐藏进度条
     */
    hide() {
        const container = document.getElementById(this.progressContainerId);
        if (container) {
            container.style.display = 'none';
        }
        this.stop();
    }

    /**
     * 启动监控
     */
    start() {
        this.show();
        this._pollStatus();
        this.pollingTimer = setInterval(() => this._pollStatus(), this.interval);
    }

    /**
     * 停止监控
     */
    stop() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            this.pollingTimer = null;
        }
    }

    /**
     * 轮询任务状态
     * @private
     */
    _pollStatus() {
        fetch(`/api/task-status/${this.taskId}`)
            .then(response => response.json())
            .then(data => {
                this.onProgress(data); // 总是报告进度
                
                if (data.state === 'SUCCESS') {
                    this.onSuccess(data.result || data);
                    this.onComplete();
                    this.stop();
                    // 延迟隐藏，让用户看到完成状态
                    setTimeout(() => this.hide(), 2000);
                } else if (data.state === 'FAILURE') {
                    this.onFailure(data.error || '未知错误');
                    this.onComplete();
                    this.stop();
                }
            })
            .catch(error => {
                console.error('查询任务状态失败:', error);
                this.onFailure('无法连接到任务服务');
                this.onComplete();
                this.stop();
            });
    }

    /**
     * 默认进度更新处理
     * @private
     */
    _defaultOnProgress(data) {
        const progressBar = document.getElementById(this.progressBarId);
        const progressText = document.getElementById(this.progressTextId);

        if (progressBar && progressText) {
            const percentage = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
            progressBar.style.width = `${percentage}%`;
            progressText.innerText = `${data.status || '处理中...'} (${percentage}%)`;
            
            // 根据状态改变颜色
            const stateClass = (data.state || 'pending').toLowerCase();
            progressBar.className = `async-progress-bar ${stateClass}`;
        }
    }

    /**
     * 默认成功处理
     * @private
     */
    _defaultOnSuccess(result) {
        console.log('任务成功完成:', result);
        alert('任务成功完成！');
    }

    /**
     * 默认失败处理
     * @private
     */
    _defaultOnFailure(error) {
        console.error('任务失败:', error);
        alert(`任务失败: ${error}`);
    }

    /**
     * 默认完成处理
     * @private
     */
    _defaultOnComplete() {
        console.log('任务监控完成');
    }
}

// 页面加载完成提示
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ AsyncTaskMonitor 类已加载');
});

