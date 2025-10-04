/**
 * 邮件分类规则管理 - 前端JavaScript
 * 提供完整的规则CRUD和交互功能
 */

// 全局变量
let currentRules = [];
let editingRuleId = null;
let sortableInstance = null;

// 分类名称映射
const categoryNames = {
    'work': '💼 工作邮件',
    'finance': '💰 财务邮件',
    'social': '👥 社交邮件',
    'shopping': '🛒 购物邮件',
    'news': '📰 资讯邮件',
    'education': '🎓 教育学习',
    'travel': '✈️ 旅行出行',
    'health': '🏥 健康医疗',
    'system': '🔔 系统通知',
    'advertising': '📢 广告邮件',
    'spam': '🗑️ 垃圾邮件',
    'general': '📁 其他邮件'
};

// 重要性名称映射
const importanceNames = {
    4: '🔴 紧急',
    3: '🟠 重要',
    2: '🟡 中等',
    1: '⚪ 普通'
};

// ========== 页面加载 ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化规则管理系统...');
    loadRules();
    loadSuggestions();
    initializeSortable();
});

// ========== 规则加载 ==========
async function loadRules() {
    try {
        console.log('正在加载规则...');
        const response = await fetch('/api/classification/rules', {
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentRules = data.rules || [];
            console.log(`加载成功: ${currentRules.length} 条规则`);
            renderRules(currentRules);
            document.getElementById('rule-count').textContent = currentRules.length;
        } else {
            console.error('加载规则失败:', data.error);
            showToast('加载规则失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('加载规则异常:', error);
        showToast('加载规则失败，请刷新页面重试', 'error');
    } finally {
        // 隐藏加载指示器
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}

function renderRules(rules) {
    const container = document.getElementById('rules-list');
    
    if (!rules || rules.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <h4 class="mt-3">还没有创建任何规则</h4>
                <p class="text-muted">点击"新建规则"按钮创建您的第一个邮件分类规则</p>
                <button class="btn btn-primary mt-3" onclick="showCreateRuleModal()">
                    <i class="fas fa-plus me-2"></i>创建第一个规则
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = rules.map(rule => `
        <div class="rule-item" data-rule-id="${rule.id}" draggable="true">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <!-- 拖拽手柄 -->
                    <span class="drag-handle me-2">
                        <i class="fas fa-grip-vertical"></i>
                    </span>
                    
                    <!-- 规则名称 -->
                    <strong class="fs-5">${escapeHtml(rule.rule_name)}</strong>
                    
                    <!-- 状态徽章 -->
                    ${rule.is_active ? 
                        '<span class="badge bg-success ms-2">启用</span>' : 
                        '<span class="badge bg-secondary ms-2">禁用</span>'}
                    
                    <!-- 优先级 -->
                    <span class="badge bg-info ms-1">
                        优先级: ${rule.priority}
                    </span>
                    
                    <!-- 匹配统计 -->
                    ${rule.match_count > 0 ? 
                        `<span class="badge bg-light text-dark ms-1">
                            已匹配 ${rule.match_count} 封
                        </span>` : ''}
                    
                    <!-- 规则详情 -->
                    <div class="mt-2 small text-muted">
                        ${renderRuleConditions(rule)}
                        <span class="mx-2">→</span>
                        <span class="text-primary fw-bold">
                            ${categoryNames[rule.target_category] || rule.target_category}
                        </span>
                        <span class="text-warning ms-2">
                            ${importanceNames[rule.target_importance] || '普通'}
                        </span>
                    </div>
                </div>
                
                <!-- 操作按钮 -->
                <div class="btn-group btn-group-sm ms-3">
                    <button class="btn btn-outline-primary" 
                            onclick="editRule(${rule.id})"
                            title="编辑规则">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-info" 
                            onclick="applyRuleToExisting(${rule.id})"
                            title="应用到现有邮件">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="btn btn-outline-danger" 
                            onclick="deleteRule(${rule.id})"
                            title="删除规则">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    
    // 重新初始化拖拽排序
    initializeSortable();
}

function renderRuleConditions(rule) {
    const conditions = [];
    
    if (rule.sender_pattern) {
        const matchType = rule.sender_match_type || 'contains';
        conditions.push(`<i class="fas fa-user me-1"></i>发件人: <code>${escapeHtml(rule.sender_pattern)}</code> (${matchType})`);
    }
    
    if (rule.subject_keywords) {
        try {
            const keywords = typeof rule.subject_keywords === 'string' 
                ? JSON.parse(rule.subject_keywords) 
                : rule.subject_keywords;
            if (keywords && keywords.length > 0) {
                const logic = rule.subject_logic || 'OR';
                conditions.push(`<i class="fas fa-heading me-1"></i>主题: <code>${keywords.join(', ')}</code> (${logic})`);
            }
        } catch (e) {
            console.error('解析主题关键词失败:', e);
        }
    }
    
    if (rule.body_keywords) {
        try {
            const keywords = typeof rule.body_keywords === 'string' 
                ? JSON.parse(rule.body_keywords) 
                : rule.body_keywords;
            if (keywords && keywords.length > 0) {
                conditions.push(`<i class="fas fa-align-left me-1"></i>正文: <code>${keywords.join(', ')}</code>`);
            }
        } catch (e) {
            console.error('解析正文关键词失败:', e);
        }
    }
    
    return conditions.length > 0 ? conditions.join(' <span class="mx-1">+</span> ') : '<span class="text-muted">无条件</span>';
}

// ========== 拖拽排序 ==========
function initializeSortable() {
    const rulesList = document.getElementById('rules-list');
    if (!rulesList) return;
    
    // 销毁旧实例
    if (sortableInstance) {
        sortableInstance.destroy();
    }
    
    // 创建新实例
    sortableInstance = new Sortable(rulesList, {
        animation: 150,
        handle: '.drag-handle',
        ghostClass: 'dragging',
        onEnd: function(evt) {
            // 更新规则顺序
            updateRulePriorities();
        }
    });
}

async function updateRulePriorities() {
    // 根据新的DOM顺序更新优先级
    const ruleItems = document.querySelectorAll('.rule-item');
    const updates = [];
    
    ruleItems.forEach((item, index) => {
        const ruleId = parseInt(item.dataset.ruleId);
        const newPriority = ruleItems.length - index; // 倒序，第一个优先级最高
        
        const rule = currentRules.find(r => r.id === ruleId);
        if (rule && rule.priority !== newPriority) {
            updates.push({
                id: ruleId,
                priority: newPriority
            });
        }
    });
    
    // 批量更新
    if (updates.length > 0) {
        console.log(`更新 ${updates.length} 条规则的优先级`);
        for (const update of updates) {
            try {
                const rule = currentRules.find(r => r.id === update.id);
                if (rule) {
                    rule.priority = update.priority;
                    await updateRuleOnServer(update.id, rule);
                }
            } catch (error) {
                console.error(`更新规则 ${update.id} 失败:`, error);
            }
        }
        showToast('规则优先级已更新', 'success');
    }
}

// ========== 规则CRUD ==========
function showCreateRuleModal() {
    editingRuleId = null;
    document.getElementById('modal-title-text').textContent = '新建规则';
    document.getElementById('ruleForm').reset();
    
    // 重置所有配置区域
    document.getElementById('enable-sender-rule').checked = false;
    document.getElementById('enable-subject-rule').checked = false;
    document.getElementById('enable-body-rule').checked = false;
    toggleSenderConfig();
    toggleSubjectConfig();
    toggleBodyConfig();
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('ruleModal'));
    modal.show();
}

async function editRule(ruleId) {
    console.log('编辑规则:', ruleId);
    editingRuleId = ruleId;
    
    const rule = currentRules.find(r => r.id === ruleId);
    if (!rule) {
        showToast('规则不存在', 'error');
        return;
    }
    
    // 填充表单
    document.getElementById('modal-title-text').textContent = '编辑规则';
    document.getElementById('rule-name').value = rule.rule_name || '';
    document.getElementById('target-category').value = rule.target_category || 'general';
    document.getElementById('target-importance').value = rule.target_importance || 2;
    document.getElementById('rule-priority').value = rule.priority || 5;
    document.getElementById('rule-active').checked = rule.is_active !== 0;
    
    // 发件人规则
    if (rule.sender_pattern) {
        document.getElementById('enable-sender-rule').checked = true;
        document.getElementById('sender-match-type').value = rule.sender_match_type || 'contains';
        document.getElementById('sender-pattern').value = rule.sender_pattern;
        toggleSenderConfig();
    } else {
        document.getElementById('enable-sender-rule').checked = false;
        toggleSenderConfig();
    }
    
    // 主题规则
    if (rule.subject_keywords) {
        document.getElementById('enable-subject-rule').checked = true;
        try {
            const keywords = typeof rule.subject_keywords === 'string' 
                ? JSON.parse(rule.subject_keywords) 
                : rule.subject_keywords;
            document.getElementById('subject-keywords').value = keywords.join(',');
            
            const logic = rule.subject_logic || 'OR';
            document.getElementById(`subject-${logic.toLowerCase()}`).checked = true;
        } catch (e) {
            console.error('解析主题关键词失败:', e);
        }
        toggleSubjectConfig();
    } else {
        document.getElementById('enable-subject-rule').checked = false;
        toggleSubjectConfig();
    }
    
    // 正文规则
    if (rule.body_keywords) {
        document.getElementById('enable-body-rule').checked = true;
        try {
            const keywords = typeof rule.body_keywords === 'string' 
                ? JSON.parse(rule.body_keywords) 
                : rule.body_keywords;
            document.getElementById('body-keywords').value = keywords.join(',');
        } catch (e) {
            console.error('解析正文关键词失败:', e);
        }
        toggleBodyConfig();
    } else {
        document.getElementById('enable-body-rule').checked = false;
        toggleBodyConfig();
    }
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('ruleModal'));
    modal.show();
}

async function saveRule() {
    const formData = collectFormData();
    
    if (!validateFormData(formData)) {
        return;
    }
    
    try {
        const url = editingRuleId 
            ? `/api/classification/rules/${editingRuleId}` 
            : '/api/classification/rules';
        const method = editingRuleId ? 'PUT' : 'POST';
        
        console.log(`${method} ${url}`, formData);
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('规则保存成功', 'success');
            bootstrap.Modal.getInstance(document.getElementById('ruleModal')).hide();
            loadRules(); // 重新加载规则列表
        } else {
            showToast('保存失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('保存规则失败:', error);
        showToast('保存规则失败，请重试', 'error');
    }
}

async function deleteRule(ruleId) {
    if (!confirm('确定要删除这条规则吗？此操作不可恢复。')) {
        return;
    }
    
    try {
        console.log('删除规则:', ruleId);
        const response = await fetch(`/api/classification/rules/${ruleId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('规则已删除', 'success');
            loadRules();
        } else {
            showToast('删除失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('删除规则失败:', error);
        showToast('删除规则失败，请重试', 'error');
    }
}

async function updateRuleOnServer(ruleId, ruleData) {
    const response = await fetch(`/api/classification/rules/${ruleId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(ruleData)
    });
    
    return await response.json();
}

// ========== 表单处理 ==========
function collectFormData() {
    const formData = {
        rule_name: document.getElementById('rule-name').value.trim(),
        target_category: document.getElementById('target-category').value,
        target_importance: parseInt(document.getElementById('target-importance').value),
        priority: parseInt(document.getElementById('rule-priority').value),
        is_active: document.getElementById('rule-active').checked
    };
    
    // 发件人规则
    if (document.getElementById('enable-sender-rule').checked) {
        formData.sender_pattern = document.getElementById('sender-pattern').value.trim();
        formData.sender_match_type = document.getElementById('sender-match-type').value;
    }
    
    // 主题规则
    if (document.getElementById('enable-subject-rule').checked) {
        const keywords = document.getElementById('subject-keywords').value
            .split(',')
            .map(k => k.trim())
            .filter(k => k);
        formData.subject_keywords = keywords;
        
        const logicRadio = document.querySelector('input[name="subject-logic"]:checked');
        formData.subject_logic = logicRadio ? logicRadio.value : 'OR';
    }
    
    // 正文规则
    if (document.getElementById('enable-body-rule').checked) {
        const keywords = document.getElementById('body-keywords').value
            .split(',')
            .map(k => k.trim())
            .filter(k => k);
        formData.body_keywords = keywords;
    }
    
    return formData;
}

function validateFormData(formData) {
    if (!formData.rule_name) {
        showToast('请输入规则名称', 'warning');
        return false;
    }
    
    if (!formData.target_category) {
        showToast('请选择目标分类', 'warning');
        return false;
    }
    
    // 检查是否至少有一个匹配条件
    const hasCondition = formData.sender_pattern || 
                        (formData.subject_keywords && formData.subject_keywords.length > 0) ||
                        (formData.body_keywords && formData.body_keywords.length > 0);
    
    if (!hasCondition) {
        showToast('请至少设置一个匹配条件', 'warning');
        return false;
    }
    
    return true;
}

// ========== 配置区域切换 ==========
function toggleSenderConfig() {
    const enabled = document.getElementById('enable-sender-rule').checked;
    const config = document.getElementById('sender-rule-config');
    config.style.display = enabled ? 'block' : 'none';
}

function toggleSubjectConfig() {
    const enabled = document.getElementById('enable-subject-rule').checked;
    const config = document.getElementById('subject-rule-config');
    config.style.display = enabled ? 'block' : 'none';
}

function toggleBodyConfig() {
    const enabled = document.getElementById('enable-body-rule').checked;
    const config = document.getElementById('body-rule-config');
    config.style.display = enabled ? 'block' : 'none';
}

// ========== 规则测试 ==========
function testCurrentRule() {
    const formData = collectFormData();
    
    if (!validateFormData(formData)) {
        return;
    }
    
    // 创建测试邮件对话框
    const testEmail = {
        sender: prompt('请输入测试邮件的发件人地址:', 'test@example.com'),
        subject: prompt('请输入测试邮件的主题:', '测试邮件主题'),
        body: prompt('请输入测试邮件的正文（可选）:', '')
    };
    
    if (!testEmail.sender || !testEmail.subject) {
        showToast('测试已取消', 'info');
        return;
    }
    
    // 调用测试API
    testRuleWithEmail(formData, testEmail);
}

async function testRuleWithEmail(rule, testEmail) {
    try {
        const response = await fetch('/api/classification/rules/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                rule: rule,
                test_email: testEmail
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const result = data.result;
            let message = `测试结果: ${result.matched ? '✅ 匹配成功' : '❌ 不匹配'}\n\n`;
            
            if (result.conditions && result.conditions.length > 0) {
                message += '条件详情:\n';
                result.conditions.forEach(cond => {
                    message += `${cond.description}\n`;
                });
            }
            
            if (result.matched) {
                message += `\n将被分类为: ${categoryNames[result.target_category]}\n`;
                message += `重要性: ${importanceNames[result.target_importance]}\n`;
                message += `得分: ${result.score.toFixed(2)}`;
            }
            
            alert(message);
        } else {
            showToast('测试失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('测试规则失败:', error);
        showToast('测试失败，请重试', 'error');
    }
}

// ========== 批量操作 ==========
async function applyRuleToExisting(ruleId) {
    if (!confirm('确定要将此规则应用到所有现有邮件吗？这可能需要一些时间。')) {
        return;
    }
    
    try {
        showToast('正在应用规则...', 'info');
        
        const response = await fetch(`/api/classification/rules/${ruleId}/apply`, {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const result = data.result;
            showToast(`已重新分类 ${result.success_count} 封邮件`, 'success');
            loadRules(); // 更新匹配统计
        } else {
            showToast('应用失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('应用规则失败:', error);
        showToast('应用规则失败，请重试', 'error');
    }
}

// ========== 导入/导出 ==========
function exportRules() {
    if (currentRules.length === 0) {
        showToast('没有规则可以导出', 'warning');
        return;
    }
    
    const dataStr = JSON.stringify(currentRules, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(dataBlob);
    downloadLink.download = `classification_rules_${new Date().toISOString().split('T')[0]}.json`;
    downloadLink.click();
    
    showToast('规则已导出', 'success');
}

function importRules() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(event) {
            try {
                const rules = JSON.parse(event.target.result);
                
                if (!Array.isArray(rules)) {
                    showToast('无效的规则文件格式', 'error');
                    return;
                }
                
                if (confirm(`确定要导入 ${rules.length} 条规则吗？`)) {
                    importRulesFromData(rules);
                }
            } catch (error) {
                console.error('解析规则文件失败:', error);
                showToast('规则文件格式错误', 'error');
            }
        };
        reader.readAsText(file);
    };
    
    input.click();
}

async function importRulesFromData(rules) {
    let successCount = 0;
    let failCount = 0;
    
    for (const rule of rules) {
        try {
            // 移除ID字段，让服务器生成新ID
            delete rule.id;
            delete rule.match_count;
            delete rule.last_matched_at;
            delete rule.created_at;
            delete rule.updated_at;
            
            const response = await fetch('/api/classification/rules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(rule)
            });
            
            const data = await response.json();
            if (data.success) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (error) {
            console.error('导入规则失败:', error);
            failCount++;
        }
    }
    
    showToast(`导入完成: 成功 ${successCount}, 失败 ${failCount}`, 'success');
    loadRules();
}

// ========== 智能建议 ==========
// ==================== 智能建议功能 ====================

/**
 * 生成智能建议
 */
async function generateSuggestions() {
    try {
        // 显示加载状态
        const btn = event.target;
        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>分析中...';
        
        showToast('正在分析您的邮件行为...', 'info');
        
        const response = await fetch('/api/classification/suggestions/generate', {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            // 重新加载建议列表
            await loadSuggestions();
        } else {
            showToast('生成建议失败: ' + (data.error || '未知错误'), 'error');
        }
        
        // 恢复按钮
        btn.disabled = false;
        btn.innerHTML = originalHTML;
        
    } catch (error) {
        console.error('生成建议失败:', error);
        showToast('生成建议失败: ' + error.message, 'error');
        event.target.disabled = false;
        event.target.innerHTML = '<i class="fas fa-lightbulb me-2"></i>生成建议';
    }
}

/**
 * 加载智能建议
 */
async function loadSuggestions() {
    try {
        const response = await fetch('/api/classification/suggestions', {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (data.suggestions && data.suggestions.length > 0) {
                renderSuggestions(data.suggestions);
            } else {
                renderNoSuggestions();
            }
        }
    } catch (error) {
        console.error('加载建议失败:', error);
    }
}

/**
 * 渲染智能建议
 */
function renderSuggestions(suggestions) {
    const container = document.getElementById('suggestions-area');
    
    const suggestionHTML = suggestions.map(sug => {
        const confidence = ((sug.confidence || 0) * 100).toFixed(0);
        const typeText = getSuggestionTypeText(sug.type);
        const categoryName = categoryNames[sug.target_category] || sug.target_category;
        
        return `
            <div class="suggestion-item" data-suggestion-id="${sug.id}">
                <div class="suggestion-header">
                    <div>
                        <span class="confidence-badge">
                            <i class="fas fa-chart-line me-1"></i>${confidence}% 置信度
                        </span>
                    </div>
                    <div>
                        <span class="suggestion-type-badge">
                            ${typeText}
                        </span>
                    </div>
                </div>
                <div class="suggestion-body">
                    <p>${escapeHtml(sug.reason || '智能分析建议')}</p>
                    <code><i class="fas fa-arrow-right me-2"></i>${escapeHtml(sug.pattern)} → ${categoryName}</code>
                </div>
                <div class="suggestion-actions">
                    <button class="btn" onclick="applySuggestion(${sug.id})">
                        <i class="fas fa-check me-1"></i>应用建议
                    </button>
                    <button class="btn btn-outline-light" onclick="ignoreSuggestion(${sug.id})">
                        <i class="fas fa-times me-1"></i>忽略
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = suggestionHTML;
}

/**
 * 渲染无建议状态
 */
function renderNoSuggestions() {
    const container = document.getElementById('suggestions-area');
    container.innerHTML = ''; // 清空，不显示任何内容
}

/**
 * 获取建议类型文本
 */
function getSuggestionTypeText(type) {
    const typeMap = {
        'sender_exact': '📧 发件人规则',
        'sender_domain': '🌐 域名规则',
        'subject_keyword': '🔤 关键词规则'
    };
    return typeMap[type] || '智能规则';
}

/**
 * 应用建议
 */
async function applySuggestion(suggestionId) {
    try {
        const btn = event.target;
        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>应用中...';
        
        const response = await fetch(`/api/classification/suggestions/${suggestionId}/apply`, {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('建议已应用，规则创建成功！', 'success');
            
            // 移除建议卡片
            const suggestionCard = document.querySelector(`[data-suggestion-id="${suggestionId}"]`);
            if (suggestionCard) {
                suggestionCard.style.transition = 'all 0.3s ease';
                suggestionCard.style.opacity = '0';
                suggestionCard.style.transform = 'translateX(-20px)';
                setTimeout(() => {
                    suggestionCard.remove();
                    
                    // 如果没有建议了，显示空状态
                    const container = document.getElementById('suggestions-area');
                    if (container.children.length === 0) {
                        renderNoSuggestions();
                    }
                }, 300);
            }
            
            // 重新加载规则列表
            loadRules();
        } else {
            showToast('应用建议失败: ' + (data.error || '未知错误'), 'error');
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
        
    } catch (error) {
        console.error('应用建议失败:', error);
        showToast('应用建议失败: ' + error.message, 'error');
        event.target.disabled = false;
        event.target.innerHTML = '<i class="fas fa-check me-1"></i>应用建议';
    }
}

/**
 * 忽略建议
 */
async function ignoreSuggestion(suggestionId) {
    if (!confirm('确定要忽略这条建议吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/classification/suggestions/${suggestionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('建议已忽略', 'info');
            
            // 移除建议卡片（动画效果）
            const suggestionCard = document.querySelector(`[data-suggestion-id="${suggestionId}"]`);
            if (suggestionCard) {
                suggestionCard.style.transition = 'all 0.3s ease';
                suggestionCard.style.opacity = '0';
                suggestionCard.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    suggestionCard.remove();
                    
                    // 如果没有建议了，显示空状态
                    const container = document.getElementById('suggestions-area');
                    if (container.children.length === 0) {
                        renderNoSuggestions();
                    }
                }, 300);
            }
        } else {
            showToast('操作失败: ' + (data.error || '未知错误'), 'error');
        }
        
    } catch (error) {
        console.error('忽略建议失败:', error);
        showToast('操作失败: ' + error.message, 'error');
    }
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    // 简化的Toast实现
    const bgColor = {
        'success': '#28a745',
        'error': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8'
    }[type] || '#6c757d';
    
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${bgColor};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        z-index: 9999;
        max-width: 300px;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);

console.log('邮件分类规则管理系统已加载');

