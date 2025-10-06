#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - AI助手服务 V2
使用Function Call实现，完全替代规则匹配
"""

import json
import logging
from typing import Dict, List, Optional

from services.ai_client import AIClient
from services.email_tools import EMAIL_TOOLS, execute_tool
from models.database import Database

logger = logging.getLogger(__name__)
# 确保日志级别
logger.setLevel(logging.INFO)


class AIAssistantServiceV2:
    """AI助手核心服务 V2 - 基于Function Call"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.db = Database()
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """创建系统提示词"""
        return """你是一个智能邮件助手，帮助用户管理和查询邮件。

**你的能力**：
1. 搜索邮件：可以根据时间、分类、发件人、关键词等条件搜索邮件
2. 统计邮件：可以统计邮件数量、分类分布、发件人分布等

**时间范围说明**：
- "今天的邮件" → today
- "昨天的邮件" → yesterday
- "本周的邮件" → this_week
- "近7天" → recent_7_days
- "本月的邮件" → this_month

**分类说明**（共12种）：
- 工作、财务、社交、购物、新闻、教育
- 旅行、健康、系统、广告、垃圾、通用

**重要性说明**：
- "重要邮件" → importance >= 3
- importance: 1=不重要, 2=一般, 3=重要, 4=很重要, 5=非常重要

**响应风格**：
- 简洁明了，重点突出
- 使用emoji增加友好感
- 如果找到邮件，简要总结关键信息
- 如果没找到，给出建设性建议
- **重要：当你收到工具执行结果后，必须用自然语言总结结果，不要只返回工具调用语句**

**示例**：
用户："今天的重要邮件"
第一步：你应该调用 search_emails(time_range="today", importance=3)
第二步：收到结果后，你应该回复："📧 找到了3封今天的重要邮件，包括：会议通知、项目进度报告、合同审批..."

用户："统计本周的邮件"
第一步：你应该调用 get_email_statistics(time_range="this_week", group_by="category")
第二步：收到结果后，你应该回复："📊 本周共收到28封邮件，其中工作邮件12封，社交邮件8封，通用邮件8封"

**关键原则**：
- 收到工具结果后，必须生成完整的自然语言回复
- 回复要包含具体数字和关键信息
- 使用友好、易懂的表达方式
"""
    
    def process_message(self, user_id: int, message: str, context: Dict = None) -> Dict:
        """
        处理用户消息（使用Function Call）
        
        Args:
            user_id: 用户ID
            message: 用户消息
            context: 上下文信息
        
        Returns:
            {
                'success': True/False,
                'response': '回复文本',
                'emails': [...],  # 相关邮件列表
                'tool_calls': [...],  # 工具调用记录
                'statistics': {...}  # 统计信息（如果有）
            }
        """
        try:
            # 同时使用 logger 和 print 确保输出
            logger.info(f"AI助手V2处理消息: 用户={user_id}, 原始问题={message}")
            print(f"\n{'=' * 80}")
            print(f"🤖 AI助手V2处理消息")
            print(f"{'=' * 80}")
            print(f"用户ID: {user_id}")
            print(f"📝 用户原始问题: {message}")
            print(f"{'=' * 80}\n")
            
            # 1. 构建对话消息（支持多轮对话）
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # 添加历史对话（如果有）
            if context and 'conversation_history' in context:
                history = context['conversation_history']
                if history:
                    # 限制历史对话数量，避免token过多（保留最近5轮对话）
                    recent_history = history[-10:] if len(history) > 10 else history
                    messages.extend(recent_history)
                    logger.info(f"✅ 加载对话历史: {len(recent_history)} 条消息（共 {len(history)} 条）")
                    print(f"✅ 加载对话历史: {len(recent_history)} 条消息")
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": message})
            
            logger.info(f"=" * 80)
            logger.info(f"开始处理用户消息")
            logger.info(f"用户ID: {user_id}")
            logger.info(f"用户消息: {message}")
            logger.info(f"消息数量: {len(messages)} (包含系统提示和历史)")
            logger.info(f"=" * 80)
            
            # 2. 第一次调用：让AI决定是否需要调用工具
            print(f"\n>>> 第一次AI调用：决策阶段")
            print(f"  - 发送消息数: {len(messages)}")
            print(f"  - 可用工具数: {len(EMAIL_TOOLS)}")
            print(f"  - Temperature: 0.3\n")
            
            logger.info(">>> 第一次AI调用：决策阶段")
            logger.info(f"  - 发送消息数: {len(messages)}")
            logger.info(f"  - 可用工具数: {len(EMAIL_TOOLS)}")
            logger.info(f"  - Temperature: 0.3")
            
            first_response = self.ai_client.chat_with_tools(
                messages=messages,
                tools=EMAIL_TOOLS,
                temperature=0.3  # 降低温度以提高准确性
            )
            
            # 检查是否有错误
            if 'error' in first_response:
                logger.error(f"❌ AI调用失败: {first_response['error']}")
                return {
                    'success': False,
                    'response': f"抱歉，处理您的请求时出现错误：{first_response['error']}",
                    'emails': [],
                    'tool_calls': []
                }
            
            tool_calls = first_response.get('tool_calls', [])
            content = first_response.get('content', '').strip()
            
            print(f"\n<<< 第一次AI调用完成")
            print(f"  - Content: '{content[:100]}'")
            print(f"  - Tool Calls: {len(tool_calls)} 个")
            print(f"  - Finish Reason: {first_response.get('finish_reason', 'unknown')}\n")
            
            # 🔧 检测并修复：如果content包含工具调用文本但tool_calls为空
            print(f"🔍 修复检测条件:")
            print(f"  - not tool_calls: {not tool_calls}")
            print(f"  - content存在: {bool(content)}")
            print(f"  - content值: '{content}'\n")
            
            if not tool_calls and content:
                tool_patterns = {
                    'search_emails': r'search_emails\((.*?)\)',
                    'get_email_statistics': r'get_email_statistics\((.*?)\)'
                }
                
                for tool_name, pattern in tool_patterns.items():
                    import re
                    match = re.search(pattern, content)
                    if match:
                        print(f"\n⚠️  检测到工具调用文本在content中: {tool_name}")
                        print(f"  原始content: {content}")
                        print(f"  正在手动解析参数...\n")
                        
                        # 解析参数
                        args_str = match.group(1)
                        try:
                            # 将参数字符串转换为字典
                            # 例如: time_range="today" -> {"time_range": "today"}
                            args_dict = {}
                            for arg in args_str.split(','):
                                if '=' in arg:
                                    key, value = arg.split('=', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"').strip("'")
                                    # 尝试转换为整数
                                    try:
                                        value = int(value)
                                    except:
                                        pass
                                    args_dict[key] = value
                            
                            # 手动构造tool_call
                            tool_calls = [{
                                'id': f'manual_call_{hash(content)}',
                                'type': 'function',
                                'function': {
                                    'name': tool_name,
                                    'arguments': json.dumps(args_dict, ensure_ascii=False)
                                }
                            }]
                            
                            print(f"  ✅ 成功解析参数: {args_dict}")
                            print(f"  已构造工具调用\n")
                            
                            # 清空content，因为已经转换为tool_calls
                            first_response['content'] = ''
                            
                        except Exception as e:
                            print(f"  ❌ 解析参数失败: {e}\n")
                        
                        break
            
            logger.info(f"<<< 第一次AI调用完成")
            logger.info(f"  - Content: '{content[:100]}'")
            logger.info(f"  - Tool Calls: {len(tool_calls)} 个（手动修复后）")
            logger.info(f"  - Finish Reason: {first_response.get('finish_reason', 'unknown')}")
            
            # 3. 如果AI决定调用工具
            if tool_calls:
                print(f"\n{'=' * 80}")
                print(f"🔧 AI决定调用 {len(tool_calls)} 个工具")
                print(f"{'=' * 80}\n")
                
                logger.info(f"\n{'=' * 80}")
                logger.info(f"🔧 AI决定调用 {len(tool_calls)} 个工具")
                logger.info(f"{'=' * 80}")
                
                tool_results = []
                emails = []
                statistics = None
                
                # 先添加 assistant 的工具调用消息（只添加一次）
                assistant_msg = {
                    "role": "assistant",
                    "content": first_response.get('content', ''),
                    "tool_calls": tool_calls
                }
                messages.append(assistant_msg)
                logger.info(f"📝 添加 assistant 消息到对话")
                logger.info(f"  - Content: '{first_response.get('content', '(空)')}'")
                logger.info(f"  - Tool Calls: {len(tool_calls)} 个")
                
                # 执行每个工具调用
                for idx, tool_call in enumerate(tool_calls, 1):
                    print(f"\n{'─' * 80}")
                    print(f"工具 {idx}/{len(tool_calls)}: 开始执行")
                    
                    tool_id = tool_call['id']
                    function_name = tool_call['function']['name']
                    
                    print(f"  - Tool ID: {tool_id}")
                    print(f"  - Function: {function_name}")
                    
                    logger.info(f"\n{'─' * 80}")
                    logger.info(f"工具 {idx}/{len(tool_calls)}: 开始执行")
                    logger.info(f"  - Tool ID: {tool_id}")
                    logger.info(f"  - Function: {function_name}")
                    
                    try:
                        arguments = json.loads(tool_call['function']['arguments'])
                        print(f"  - Arguments: {json.dumps(arguments, ensure_ascii=False)}")
                        logger.info(f"  - Arguments: {json.dumps(arguments, ensure_ascii=False)}")
                    except json.JSONDecodeError as e:
                        print(f"  ❌ 解析工具参数失败: {e}")
                        logger.error(f"  ❌ 解析工具参数失败: {e}")
                        logger.error(f"  原始参数: {tool_call['function']['arguments']}")
                        arguments = {}
                    
                    print(f"  ⚙️  开始执行工具...")
                    logger.info(f"  ⚙️  开始执行工具...")
                    
                    # 执行工具
                    result = execute_tool(function_name, arguments, user_id)
                    tool_results.append(result)
                    
                    print(f"  ✅ 工具执行完成")
                    print(f"  - Success: {result.get('success', False)}")
                    print(f"  - Count: {result.get('count', 0)}")
                    
                    logger.info(f"  ✅ 工具执行完成")
                    logger.info(f"  - Success: {result.get('success', False)}")
                    logger.info(f"  - Count: {result.get('count', 0)}")
                    if 'error' in result:
                        print(f"  - Error: {result['error']}")
                        logger.error(f"  - Error: {result['error']}")
                    
                    # 收集邮件和统计信息
                    if 'emails' in result:
                        email_count = len(result['emails'])
                        emails.extend(result['emails'])
                        logger.info(f"  - 收集了 {email_count} 封邮件，累计: {len(emails)} 封")
                    if 'statistics' in result:
                        statistics = result
                        logger.info(f"  - 收集了统计信息: {result.get('total', 0)} 条记录")
                    
                    # 将每个工具的结果添加到对话中
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": function_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    }
                    messages.append(tool_msg)
                    logger.info(f"  📝 添加 tool 消息到对话")
                    logger.info(f"  - Tool Call ID: {tool_id}")
                    logger.info(f"  - Content Length: {len(tool_msg['content'])} 字符")
                
                # 4. 第二次调用：让AI根据工具结果生成最终回复
                print(f"\n{'=' * 80}")
                print(f">>> 第二次AI调用：生成最终回复")
                print(f"  - 发送消息数: {len(messages)}")
                print(f"  - 包含邮件数: {len(emails)}")
                print(f"  - 包含统计: {'是' if statistics else '否'}")
                print(f"  - Temperature: 0.7\n")
                
                logger.info(f"\n{'=' * 80}")
                logger.info(f">>> 第二次AI调用：生成最终回复")
                logger.info(f"  - 发送消息数: {len(messages)}")
                logger.info(f"  - 包含邮件数: {len(emails)}")
                logger.info(f"  - 包含统计: {'是' if statistics else '否'}")
                logger.info(f"  - Temperature: 0.7")
                
                final_response = self.ai_client.chat_with_tools(
                    messages=messages,
                    tools=EMAIL_TOOLS,
                    temperature=0.7
                )
                
                print(f"\n<<< 第二次AI调用完成")
                response_text = final_response.get('content', '').strip()
                print(f"  - Content Length: {len(response_text)} 字符")
                print(f"  - Content Preview: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'")
                print(f"  - Finish Reason: {final_response.get('finish_reason', 'unknown')}\n")
                
                print(f"📊 问题与回复分析:")
                print(f"  - 用户原始问题: {message}")
                print(f"  - AI理解并调用: {len(tool_calls)} 个工具")
                print(f"  - 工具返回结果: {len(emails)} 封邮件")
                print(f"  - AI最终回复: {response_text[:80]}{'...' if len(response_text) > 80 else ''}\n")
                
                logger.info(f"<<< 第二次AI调用完成")
                logger.info(f"  - Content Length: {len(response_text)} 字符")
                logger.info(f"  - Content Preview: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'")
                logger.info(f"  - Finish Reason: {final_response.get('finish_reason', 'unknown')}")
                logger.info(f"📊 问题与回复分析: 原始问题='{message}', 调用工具={len(tool_calls)}个, 返回邮件={len(emails)}封")
                
                # 检查是否返回了工具调用语句（而不是自然语言）
                is_tool_call_text = False
                if response_text:
                    # 检查是否包含工具调用的特征
                    tool_patterns = ['search_emails(', 'get_email_statistics(', 'get_unread_emails(']
                    is_tool_call_text = any(pattern in response_text for pattern in tool_patterns)
                    if is_tool_call_text:
                        logger.warning(f"\n⚠️  检测到工具调用语句")
                        logger.warning(f"  返回内容: {response_text}")
                        logger.warning(f"  这不是自然语言回复，将使用降级回复")
                
                # 如果AI没有生成回复、返回空内容或只返回工具调用语句，生成详细回复
                if not response_text or is_tool_call_text:
                    print(f"\n{'⚠️ ' * 40}")
                    print(f"⚠️  触发降级回复机制")
                    if not response_text:
                        print(f"  原因: AI返回空content")
                    if is_tool_call_text:
                        print(f"  原因: AI返回工具调用语句")
                    print(f"  邮件数: {len(emails)}")
                    print(f"  统计数: {1 if statistics else 0}")
                    print(f"{'⚠️ ' * 40}\n")
                    
                    logger.warning(f"\n{'⚠️ ' * 40}")
                    logger.warning(f"触发降级回复机制")
                    if not response_text:
                        logger.warning(f"  原因: AI返回空content")
                    if is_tool_call_text:
                        logger.warning(f"  原因: AI返回工具调用语句")
                    logger.warning(f"  邮件数: {len(emails)}")
                    logger.warning(f"  统计数: {1 if statistics else 0}")
                    logger.warning(f"{'⚠️ ' * 40}\n")
                    if emails:
                        # 生成邮件摘要
                        response_text = f"📧 找到了 {len(emails)} 封邮件"
                        
                        # 按分类统计
                        category_counts = {}
                        for email in emails:
                            category = email.get('category', '通用')
                            category_counts[category] = category_counts.get(category, 0) + 1
                        
                        # 添加分类摘要
                        if category_counts:
                            category_summary = []
                            # 完整的12种分类映射
                            category_names = {
                                'work': '工作', 'finance': '财务', 'social': '社交', 
                                'shopping': '购物', 'news': '新闻', 'education': '教育',
                                'travel': '旅行', 'health': '健康', 'system': '系统',
                                'advertising': '广告', 'spam': '垃圾', 'general': '通用'
                            }
                            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                                cat_name = category_names.get(cat, cat)
                                category_summary.append(f"{cat_name}邮件{count}封")
                            response_text += f"，包括：{' '.join(category_summary[:3])}"
                        
                        # 添加前3封邮件的主题
                        if len(emails) > 0:
                            response_text += "\n\n主要邮件："
                            for i, email in enumerate(emails[:3], 1):
                                subject = email.get('subject', '无主题')[:40]
                                sender = email.get('sender', '未知')
                                # 提取发件人名称
                                if '<' in sender:
                                    sender = sender.split('<')[0].strip().strip('"')
                                response_text += f"\n{i}. {subject} - {sender}"
                            
                            if len(emails) > 3:
                                response_text += f"\n... 以及其他 {len(emails) - 3} 封邮件"
                    
                    elif statistics:
                        # 生成统计摘要
                        total = statistics.get('total', 0)
                        stats = statistics.get('statistics', [])
                        response_text = f"📊 统计信息：共 {total} 封邮件"
                        
                        if stats:
                            response_text += "\n\n分类统计："
                            category_names = {'work': '工作', 'finance': '财务', 'social': '社交', 
                                            'shopping': '购物', 'news': '新闻', 'general': '通用'}
                            for item in stats[:5]:  # 最多显示5个分类
                                category = item.get('category') or item.get('sender') or item.get('date')
                                count = item.get('count', 0)
                                cat_name = category_names.get(category, category)
                                response_text += f"\n• {cat_name}: {count} 封"
                    
                    else:
                        response_text = "✅ 查询完成，但没有找到符合条件的邮件"
                
                print(f"\n{'=' * 80}")
                print(f"✅ 处理完成")
                print(f"  - 用户原始问题: {message}")
                print(f"  - 最终回复长度: {len(response_text)} 字符")
                print(f"  - 返回邮件数: {len(emails)}")
                print(f"  - 工具调用数: {len(tool_calls)}")
                print(f"  - 是否降级: {'是' if (not final_response.get('content', '').strip() or is_tool_call_text) else '否'}")
                print(f"  - 回复准确性: {'✅ 自然语言' if not is_tool_call_text else '⚠️ 工具调用文本'}")
                print(f"{'=' * 80}\n")
                
                logger.info(f"\n{'=' * 80}")
                logger.info(f"✅ 处理完成")
                logger.info(f"  - 用户原始问题: {message}")
                logger.info(f"  - 最终回复长度: {len(response_text)} 字符")
                logger.info(f"  - 返回邮件数: {len(emails)}")
                logger.info(f"  - 工具调用数: {len(tool_calls)}")
                logger.info(f"  - 是否降级: {'是' if (not final_response.get('content', '').strip() or is_tool_call_text) else '否'}")
                logger.info(f"  - 回复准确性: {'自然语言' if not is_tool_call_text else '工具调用文本'}")
                logger.info(f"{'=' * 80}\n")
                
                return {
                    'success': True,
                    'response': response_text,
                    'emails': emails,  # 返回所有邮件到前端
                    'tool_calls': tool_calls,
                    'statistics': statistics
                }
            
            # 5. 没有工具调用：直接返回AI的回复
            else:
                print(f"\n⚠️  没有工具调用，直接返回AI回复")
                print(f"  - 用户原始问题: {message}")
                print(f"  - response_text: '{first_response.get('content', '')[:100]}'")
                print(f"  - tool_calls数量: {len(tool_calls)}\n")
                
                logger.info(f"AI没有调用工具，直接回复 - 用户问题: {message}")
                response_text = first_response.get('content', '您好！我是您的邮件助手，有什么可以帮您的吗？')
                
                print(f"{'=' * 80}")
                print(f"✅ 处理完成（无工具调用）")
                print(f"  - 用户原始问题: {message}")
                print(f"  - AI直接回复: {response_text[:80]}{'...' if len(response_text) > 80 else ''}")
                print(f"{'=' * 80}\n")
                
                logger.info(f"✅ 处理完成（无工具调用） - 问题: {message}, 回复: {response_text[:80]}")
                
                return {
                    'success': True,
                    'response': response_text,
                    'emails': [],
                    'tool_calls': []
                }
        
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            return {
                'success': False,
                'response': '抱歉，处理您的请求时出现了错误。请稍后再试。',
                'emails': [],
                'tool_calls': [],
                'error': str(e)
            }
    
    def process_message_stream(self, user_id: int, message: str, context: Dict = None):
        """
        流式处理用户消息（暂不支持Function Call的流式）
        
        注意：Function Call暂不支持流式，此方法返回完整结果
        """
        # Function Call不支持流式，直接返回完整结果
        result = self.process_message(user_id, message, context)
        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

