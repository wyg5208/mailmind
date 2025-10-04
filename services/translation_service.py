#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译服务模块
使用GLM大模型进行英文到中文的翻译
"""

import re
import logging
import requests
import threading
from typing import Optional, Dict, Callable
from config import Config
from models.database import Database

logger = logging.getLogger(__name__)

class TranslationService:
    """翻译服务类"""
    
    def __init__(self):
        """初始化翻译服务"""
        self.db = Database()
        self._init_client()
    
    def _init_client(self):
        """初始化GLM客户端配置"""
        try:
            # 优先从数据库加载配置
            self.api_key = self.db.get_system_config('glm_api_key', Config.GLM_API_KEY)
            self.base_url = Config.GLM_BASE_URL
            self.model = self.db.get_system_config('glm_model', Config.GLM_MODEL)
            
            if not self.api_key:
                logger.warning("GLM API key 未配置，翻译功能将不可用")
        except Exception as e:
            logger.error(f"初始化翻译服务配置失败: {e}")
            # 使用默认配置
            self.api_key = Config.GLM_API_KEY
            self.base_url = Config.GLM_BASE_URL
            self.model = Config.GLM_MODEL
    
    def _is_english_text(self, text: str) -> bool:
        """判断文本是否主要为英文"""
        if not text or not text.strip():
            return False
        
        # 移除标点符号和数字
        clean_text = re.sub(r'[^\w\s]', '', text)
        clean_text = re.sub(r'\d+', '', clean_text)
        
        if not clean_text.strip():
            return False
        
        # 计算英文字符占比
        english_chars = len(re.findall(r'[a-zA-Z]', clean_text))
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', clean_text))
        total_chars = english_chars + chinese_chars
        
        if total_chars == 0:
            return False
        
        # 如果英文字符占比超过70%，认为是英文文本
        english_ratio = english_chars / total_chars
        return english_ratio > 0.7
    
    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否主要为中文"""
        if not text or not text.strip():
            return False
        
        # 移除标点符号和数字
        clean_text = re.sub(r'[^\w\s]', '', text)
        clean_text = re.sub(r'\d+', '', clean_text)
        
        if not clean_text.strip():
            return False
        
        # 计算中文字符占比
        english_chars = len(re.findall(r'[a-zA-Z]', clean_text))
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', clean_text))
        total_chars = english_chars + chinese_chars
        
        if total_chars == 0:
            return False
        
        # 如果中文字符占比超过70%，认为是中文文本
        chinese_ratio = chinese_chars / total_chars
        return chinese_ratio > 0.7
    
    def _is_mixed_text(self, text: str) -> bool:
        """判断文本是否为中英文混合"""
        if not text or not text.strip():
            return False
        
        # 移除标点符号和数字
        clean_text = re.sub(r'[^\w\s]', '', text)
        clean_text = re.sub(r'\d+', '', clean_text)
        
        if not clean_text.strip():
            return False
        
        # 计算中英文字符占比
        english_chars = len(re.findall(r'[a-zA-Z]', clean_text))
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', clean_text))
        total_chars = english_chars + chinese_chars
        
        if total_chars == 0:
            return False
        
        english_ratio = english_chars / total_chars
        chinese_ratio = chinese_chars / total_chars
        
        # 如果中英文字符占比都在30%-70%之间，认为是混合文本
        return 0.3 <= english_ratio <= 0.7 and 0.3 <= chinese_ratio <= 0.7
    
    def _create_translation_prompt(self, text: str) -> str:
        """创建翻译提示词"""
        prompt = f"""
请将以下英文文本翻译成简洁准确的中文，保持原文的含义和语气：

英文原文：{text}

翻译要求：
1. 翻译成自然流畅的中文
2. 保持原文的核心信息和重要细节
3. 如果是邮件摘要，保持摘要的简洁性
4. 专业术语请使用准确的中文表达
5. 时间、日期、金额等关键信息保持准确
6. 只返回翻译结果，不要添加任何解释

中文翻译："""
        
        return prompt.strip()
    
    def _create_english_translation_prompt(self, text: str) -> str:
        """创建英文翻译提示词"""
        prompt = f"""
请将以下中文文本翻译成简洁准确的英文，保持原文的含义和语气：

中文原文：{text}

翻译要求：
1. 翻译成自然流畅的英文
2. 保持原文的核心信息和重要细节
3. 如果是邮件摘要，保持摘要的简洁性
4. 专业术语请使用准确的英文表达
5. 时间、日期、金额等关键信息保持准确
6. 只返回翻译结果，不要添加任何解释

英文翻译："""
        
        return prompt.strip()
    
    def _create_mixed_to_chinese_prompt(self, text: str) -> str:
        """创建混合文本到中文翻译提示词"""
        prompt = f"""
请将以下中英文混合文本翻译成完整的中文，保持原文的含义和语气：

原文：{text}

翻译要求：
1. 将所有英文部分翻译成中文
2. 中文部分保持不变
3. 保持原文的核心信息和重要细节
4. 专业术语请使用准确的中文表达
5. 时间、日期、金额等关键信息保持准确
6. 只返回翻译结果，不要添加任何解释

中文翻译："""
        
        return prompt.strip()
    
    def _create_mixed_to_english_prompt(self, text: str) -> str:
        """创建混合文本到英文翻译提示词"""
        prompt = f"""
请将以下中英文混合文本翻译成完整的英文，保持原文的含义和语气：

原文：{text}

翻译要求：
1. 将所有中文部分翻译成英文
2. 英文部分保持不变
3. 保持原文的核心信息和重要细节
4. 专业术语请使用准确的英文表达
5. 时间、日期、金额等关键信息保持准确
6. 只返回翻译结果，不要添加任何解释

英文翻译："""
        
        return prompt.strip()
    
    def _call_glm_translation_api(self, prompt: str) -> Optional[str]:
        """调用GLM API进行翻译"""
        if not self.api_key:
            logger.error("GLM API key 未配置，无法进行翻译")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.3,  # 降低随机性，提高翻译准确性
            'max_tokens': 1000,
            'top_p': 0.8,
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and result['choices']:
                    translation = result['choices'][0]['message']['content'].strip()
                    # 清理翻译结果
                    translation = self._clean_translation_result(translation)
                    return translation
                else:
                    logger.error("GLM API 翻译返回格式错误")
                    return None
            else:
                error_text = response.text
                logger.error(f"GLM API 翻译调用失败: {response.status_code} - {error_text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("GLM API 翻译调用超时")
            return None
        except Exception as e:
            logger.error(f"GLM API 翻译调用异常: {e}")
            return None
    
    def _clean_translation_result(self, translation: str) -> str:
        """清理翻译结果"""
        if not translation:
            return ""
        
        # 移除可能的提示词残留
        translation = re.sub(r'^中文翻译[:：]\s*', '', translation)
        translation = re.sub(r'^英文翻译[:：]\s*', '', translation)
        translation = re.sub(r'^翻译[:：]\s*', '', translation)
        translation = re.sub(r'^翻译结果[:：]\s*', '', translation)
        
        # 移除引号（如果整个翻译被引号包围）
        translation = translation.strip()
        if (translation.startswith('"') and translation.endswith('"')) or \
           (translation.startswith('"') and translation.endswith('"')) or \
           (translation.startswith('「') and translation.endswith('」')):
            translation = translation[1:-1].strip()
        
        return translation.strip()
    
    def translate_to_chinese(self, text: str) -> str:
        """将文本翻译成中文（同步方法）"""
        try:
            # 检查是否需要翻译
            if not self._is_english_text(text):
                logger.debug("文本不是英文或已是中文，无需翻译")
                return text
            
            # 创建翻译提示词
            prompt = self._create_translation_prompt(text)
            
            # 调用GLM API进行翻译
            translation = self._call_glm_translation_api(prompt)
            
            if translation:
                logger.info(f"翻译成功: {text[:50]}... -> {translation[:50]}...")
                return translation
            else:
                logger.warning(f"翻译失败，返回原文: {text[:50]}...")
                return text
                
        except Exception as e:
            logger.error(f"翻译过程出错: {e}")
            return text
    
    def translate_to_english(self, text: str) -> str:
        """将文本翻译成英文（同步方法）"""
        try:
            # 检查是否需要翻译
            if not self._is_chinese_text(text):
                logger.debug("文本不是中文或已是英文，无需翻译")
                return text
            
            # 创建翻译提示词
            prompt = self._create_english_translation_prompt(text)
            
            # 调用GLM API进行翻译
            translation = self._call_glm_translation_api(prompt)
            
            if translation:
                logger.info(f"英文翻译成功: {text[:50]}... -> {translation[:50]}...")
                return translation
            else:
                logger.warning(f"英文翻译失败，返回原文: {text[:50]}...")
                return text
                
        except Exception as e:
            logger.error(f"英文翻译过程出错: {e}")
            return text
    
    def translate_mixed_to_chinese(self, text: str) -> str:
        """将混合文本翻译成完整中文"""
        try:
            # 如果是纯中文，直接返回
            if self._is_chinese_text(text):
                return text
            
            # 创建混合文本到中文翻译提示词
            prompt = self._create_mixed_to_chinese_prompt(text)
            
            # 调用GLM API进行翻译
            translation = self._call_glm_translation_api(prompt)
            
            if translation:
                logger.info(f"混合文本中文翻译成功: {text[:50]}... -> {translation[:50]}...")
                return translation
            else:
                logger.warning(f"混合文本中文翻译失败，返回原文: {text[:50]}...")
                return text
                
        except Exception as e:
            logger.error(f"混合文本中文翻译过程出错: {e}")
            return text
    
    def translate_mixed_to_english(self, text: str) -> str:
        """将混合文本翻译成完整英文"""
        try:
            # 如果是纯英文，直接返回
            if self._is_english_text(text):
                return text
            
            # 创建混合文本到英文翻译提示词
            prompt = self._create_mixed_to_english_prompt(text)
            
            # 调用GLM API进行翻译
            translation = self._call_glm_translation_api(prompt)
            
            if translation:
                logger.info(f"混合文本英文翻译成功: {text[:50]}... -> {translation[:50]}...")
                return translation
            else:
                logger.warning(f"混合文本英文翻译失败，返回原文: {text[:50]}...")
                return text
                
        except Exception as e:
            logger.error(f"混合文本英文翻译过程出错: {e}")
            return text
    
    def smart_translate_to_chinese(self, text: str) -> str:
        """智能翻译到中文：纯中文保持原文，纯英文或混合文本翻译为中文"""
        try:
            if self._is_chinese_text(text):
                # 纯中文，保持原文
                return text
            elif self._is_english_text(text):
                # 纯英文，翻译为中文
                return self.translate_to_chinese(text)
            elif self._is_mixed_text(text):
                # 混合文本，翻译为完整中文
                return self.translate_mixed_to_chinese(text)
            else:
                # 无法判断类型，返回原文
                return text
        except Exception as e:
            logger.error(f"智能中文翻译出错: {e}")
            return text
    
    def smart_translate_to_english(self, text: str) -> str:
        """智能翻译到英文：纯英文保持原文，纯中文或混合文本翻译为英文"""
        try:
            if self._is_english_text(text):
                # 纯英文，保持原文
                return text
            elif self._is_chinese_text(text):
                # 纯中文，翻译为英文
                return self.translate_to_english(text)
            elif self._is_mixed_text(text):
                # 混合文本，翻译为完整英文
                return self.translate_mixed_to_english(text)
            else:
                # 无法判断类型，返回原文
                return text
        except Exception as e:
            logger.error(f"智能英文翻译出错: {e}")
            return text

    def translate_to_chinese_async(self, text: str, callback: Callable[[str], None]):
        """异步翻译文本到中文"""
        def _translate_worker():
            try:
                result = self.translate_to_chinese(text)
                callback(result)
            except Exception as e:
                logger.error(f"异步翻译出错: {e}")
                callback(text)  # 返回原文
        
        # 在新线程中执行翻译
        thread = threading.Thread(target=_translate_worker, daemon=True)
        thread.start()
    
    def batch_translate_to_chinese(self, texts: list) -> list:
        """批量翻译文本到中文"""
        if not texts:
            return []
        
        translated_texts = []
        for text in texts:
            try:
                translated = self.translate_to_chinese(text)
                translated_texts.append(translated)
            except Exception as e:
                logger.error(f"批量翻译单项失败: {e}")
                translated_texts.append(text)  # 保留原文
        
        return translated_texts
    
    def is_translation_available(self) -> bool:
        """检查翻译功能是否可用"""
        return bool(self.api_key and self.base_url and self.model)

# 创建全局翻译服务实例
translation_service = TranslationService()
