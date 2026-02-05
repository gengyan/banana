"""
提示词优化器

使用 Gemini 2.0 Flash Exp (gemini-2.0-flash-exp) 模型优化图片生成提示词
"""
import re
import time
import logging
import traceback
import google.api_core.exceptions as gexceptions
import google.generativeai as genai

# 尝试导入 GenerationConfig（如果可用）
try:
    from google.generativeai.types import GenerationConfig
    GENERATION_CONFIG_AVAILABLE = True
except (ImportError, AttributeError):
    GENERATION_CONFIG_AVAILABLE = False
    logger = logging.getLogger("果捷后端")
    logger.warning("⚠️ GenerationConfig 不可用，翻译时将仅依赖指令确保精准度")

logger = logging.getLogger("果捷后端")


def optimize_prompt(prompt: str) -> str:
    """
    使用 Gemini 2.0 Flash Exp 模型优化图片生成提示词
    
    ⚠️ 重要：这是文本生成函数，只返回文本，不生成图片
    - 模型: gemini-2.0-flash-exp（文本生成模型）
    - API: model.generate_content()（文本生成 API）
    - 响应: response.text（文本响应）
    
    功能：将用户的简短提示词优化为详细的图片生成提示词（纯文本处理）
    
    Args:
        prompt: 原始提示词
    
    Returns:
        优化后的提示词，如果优化失败则返回原始提示词
    """
    try:
        # 使用 gemini-2.0-flash-exp 模型
        model_name = 'gemini-2.0-flash-exp'
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"❌ 模型 {model_name} 不可用: {e}")
            logger.warning("⚠️ 提示词优化失败，使用原始提示词")
            return prompt
        
        # 优化提示词（带重试机制）
        optimized_prompt = prompt
        max_retries = 3
        retry_delay = 2
        
        # ⚠️ 重要：检测是否为翻译请求（SD3.5 模式使用）
        # 如果 prompt 包含翻译指令，执行精准直译，不做优化
        is_translation_request = (
            "请将以下中文" in prompt or 
            "翻译成英文" in prompt or 
            "translate" in prompt.lower() or
            "translation" in prompt.lower() or
            "仅直译" in prompt or
            "不要扩展" in prompt
        )
        
        for attempt in range(max_retries):
            try:
                if is_translation_request:
                    # ⚠️ 翻译模式：精准直译，不做优化或扩展
                    # 使用更低的 temperature (0.0-0.1) 来确保翻译更精准、一致
                    logger.info(f"🌐 检测到翻译请求，执行精准直译模式")
                    logger.info(f"   ⚠️ 要求：只做直译，不扩展或添加细节")
                    logger.info(f"   ⚠️ 要求：保持原意完全不变，不添加视觉细节描述")
                    optimization_request = prompt  # 直接使用前端传入的翻译指令
                    # ⚠️ 注意：旧版 google.generativeai 使用 generation_config 参数
                    # 但需要确认是否支持，如果不支持则仅依赖指令来保证精准翻译
                    # ⚠️ 尝试使用 generation_config 参数设置低 temperature (0.0) 确保翻译精准
                    # 如果 API 不支持 generation_config，将仅依赖翻译指令确保精准度
                    try:
                        if GENERATION_CONFIG_AVAILABLE:
                            # 使用 GenerationConfig 对象
                            response = model.generate_content(
                                optimization_request,
                                generation_config=GenerationConfig(
                                    temperature=0.0,  # 最低温度，确保翻译最精准、一致（不添加额外内容）
                                    top_p=0.7,  # 降低随机性
                                    top_k=20,  # 限制候选词数量，减少变化
                                )
                            )
                            logger.info(f"✅ 使用 GenerationConfig (temperature=0.0) 确保精准翻译")
                        else:
                            # GenerationConfig 不可用，尝试字典格式
                            try:
                                response = model.generate_content(
                                    optimization_request,
                                    generation_config={
                                        'temperature': 0.0,  # 最低温度，确保翻译最精准、一致
                                        'top_p': 0.7,  # 降低随机性
                                        'top_k': 20,  # 限制候选词数量
                                    }
                                )
                                logger.info(f"✅ 使用字典格式 generation_config (temperature=0.0) 确保精准翻译")
                            except (TypeError, AttributeError) as dict_error:
                                # 如果字典格式也不支持，仅使用指令确保精准翻译
                                logger.warning(f"⚠️ generation_config 参数不支持，仅依赖翻译指令确保精准翻译")
                                logger.warning(f"   错误: {dict_error}")
                                logger.warning(f"   💡 翻译精准度将完全依赖指令，不依赖 temperature 参数")
                                response = model.generate_content(optimization_request)
                    except Exception as config_error:
                        # 如果所有方式都失败，仅使用指令确保精准翻译
                        logger.warning(f"⚠️ 设置 generation_config 失败，仅依赖翻译指令: {config_error}")
                        logger.warning(f"   💡 翻译精准度将完全依赖指令，不依赖 temperature 参数")
                        response = model.generate_content(optimization_request)
                else:
                    # 优化模式：润色提示词，使其更详细、具体，适合图片生成
                    # 重要：优化后的提示词必须在150字以内（中文字符数）
                    logger.info(f"📝 检测到优化请求，执行提示词优化模式")
                    optimization_request = f"""你是一位专业的图片生成提示词优化师。请将以下用户的图片生成提示词润色优化，使其更加详细、具体、生动，包含更多视觉细节（如光线、色彩、构图、风格、材质等），以便AI图片生成模型能够生成更高质量的图片。

要求：
1. 保持原意不变，只做润色和增强
2. 添加更多视觉细节描述（光照、色彩、材质、风格等）
3. 输出完整的、可直接用于图片生成的提示词
4. 不要添加任何说明文字，只输出优化后的提示词本身
5. 使用英文或中文都可以，但要清晰准确
6. 优化后的提示词必须在150字以内（中文字符数），如果原提示词已接近或超过150字，则保持简洁或适当精简

原始提示词：{prompt}

优化后的提示词（150字以内）："""
                    response = model.generate_content(optimization_request)
                
                optimized_prompt = response.text.strip()
                
                logger.info(f"📝 文本模型返回的原始结果: {optimized_prompt[:150]}...")
                
                # 清理返回的内容：移除可能的说明文字、模板占位符等
                # 如果包含换行，取第一段（通常是优化后的提示词）
                if '\n' in optimized_prompt:
                    lines = optimized_prompt.split('\n')
                    # 找到第一个不包含"提示词"、"优化"等关键词的行
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 5 and not any(keyword in line.lower() for keyword in ['提示词', '优化', 'prompt', 'optimized', 'original', '原始', '以下是', '如下', 'answer']):
                            optimized_prompt = line
                            logger.info(f"✅ 提取到优化后的提示词（从多行中）: {optimized_prompt[:100]}...")
                            break
                    else:
                        # 如果都包含关键词，使用第一行（但确保不是说明文字）
                        if lines:
                            first_line = lines[0].strip()
                            if len(first_line) > 10:  # 确保不是太短的说明文字
                                optimized_prompt = first_line
                
                # 验证优化后的提示词是否有效
                if not optimized_prompt or len(optimized_prompt.strip()) < 3:
                    logger.warning("⚠️ 优化后的提示词太短或为空，使用原始提示词")
                    optimized_prompt = prompt
                
                # 移除可能的模板占位符
                if '[' in optimized_prompt and ']' in optimized_prompt:
                    logger.warning("⚠️ 优化后的提示词包含模板占位符，尝试清理...")
                    # 简单处理：如果包含太多占位符，使用原始提示词
                    placeholder_count = optimized_prompt.count('[')
                    if placeholder_count > 2:
                        logger.warning("⚠️ 提示词包含过多占位符，使用原始提示词")
                        optimized_prompt = prompt
                
                # 检查字数：优化后的提示词必须在150个汉字或150个单词以内
                # 判断是中文还是英文：如果中文字符超过30%，按汉字计算；否则按单词计算
                chinese_char_count = len([c for c in optimized_prompt if '\u4e00' <= c <= '\u9fff'])
                total_char_count = len(optimized_prompt)
                chinese_ratio = chinese_char_count / total_char_count if total_char_count > 0 else 0
                
                max_limit = 150
                is_chinese = chinese_ratio > 0.3
                
                if is_chinese:
                    # 中文：按字符数计算（1个汉字 = 1个字符）
                    current_count = total_char_count
                    logger.info(f"📝 提示词为中文，当前字数: {current_count}字")
                else:
                    # 英文：按单词数计算
                    words = re.findall(r'\b\w+\b', optimized_prompt)
                    current_count = len(words)
                    logger.info(f"📝 提示词为英文，当前单词数: {current_count}个")
                
                if current_count > max_limit:
                    logger.warning(f"⚠️ 优化后的提示词超过限制（{current_count} {'字' if is_chinese else '个单词'}），进行截断...")
                    # 截断处理
                    if is_chinese:
                        # 中文：按字符数截断
                        truncated = optimized_prompt[:max_limit]
                        # 尝试在最后一个标点符号处截断，使提示词更完整
                        for punct in ['。', '，', '、', '；', '！', '？', '.', ',', ';', '!', '?']:
                            last_punct = truncated.rfind(punct)
                            if last_punct > max_limit * 0.7:  # 至少保留70%的内容
                                truncated = truncated[:last_punct + 1]
                                break
                        optimized_prompt = truncated
                        logger.info(f"✅ 提示词已截断至{len(optimized_prompt)}字: {optimized_prompt[:100]}...")
                    else:
                        # 英文：按单词数截断
                        if len(words) > max_limit:
                            # 截断到150个单词
                            truncated_words = words[:max_limit]
                            # 找到最后一个单词在原文本中的位置
                            last_word = truncated_words[-1]
                            last_index = optimized_prompt.rfind(last_word)
                            if last_index != -1:
                                # 包含最后一个单词及之后可能的标点符号
                                next_char_idx = last_index + len(last_word)
                                # 找到单词后的空格或标点
                                while next_char_idx < len(optimized_prompt) and optimized_prompt[next_char_idx] in ' .,;!?':
                                    next_char_idx += 1
                                optimized_prompt = optimized_prompt[:next_char_idx]
                            else:
                                # 如果找不到，简单拼接单词
                                optimized_prompt = ' '.join(truncated_words)
                        # 计算单词数（避免在f-string中使用反斜杠）
                        word_pattern = re.compile(r'\b\w+\b')
                        word_count = len(word_pattern.findall(optimized_prompt))
                        logger.info(f"✅ 提示词已截断至约{word_count}个单词: {optimized_prompt[:100]}...")
                else:
                    logger.info(f"✅ 提示词长度符合要求（{current_count} {'字' if is_chinese else '个单词'}）")
                
                logger.info(f"✅ 提示词润色完成 (尝试 {attempt + 1}/{max_retries}): {optimized_prompt[:100]}...")
                return optimized_prompt
            except (gexceptions.ServiceUnavailable, gexceptions.RetryError) as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ 提示词润色失败 (尝试 {attempt + 1}/{max_retries})，{retry_delay}秒后重试: {error_msg[:100]}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.warning(f"⚠️ 提示词润色失败，已重试{max_retries}次，使用原始提示词: {error_msg[:100]}")
                    return prompt
            except Exception as e:
                logger.warning(f"⚠️ 提示词润色异常，使用原始提示词: {str(e)[:100]}")
                return prompt
        
        return prompt
    except Exception as e:
        logger.error(f"❌ 提示词优化失败: {e}")
        logger.error(traceback.format_exc())
        return prompt
