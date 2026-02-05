"""
Banana Image 请求处理器 - 统一图像生成接口
支持 Gemini 2.5 Flash Image 和 Gemini 3 Pro Image
"""
import io
import time
from typing import Optional, List, Tuple, Dict, Any
from fastapi import Request, UploadFile
from PIL import Image

from log_utils import log_info, log_error, log_warning, log_success


class BananaImageRequest:
    """请求数据模型"""
    
    def __init__(self):
        self.request_id = f"{int(time.time() * 1000)}"
        self.message = ""
        self.mode = "banana"
        self.aspect_ratio = None
        self.resolution = None
        self.skip_optimization = False
        self.reference_images: List[Image.Image] = []
    
    def is_valid(self) -> Tuple[bool, Optional[str]]:
        """验证请求数据"""
        if not self.message:
            return False, "消息内容不能为空"
        return True, None


class FormDataParser:
    """FormData 请求解析器"""
    
    @staticmethod
    async def parse(request: Request, req_data: BananaImageRequest) -> bool:
        """
        解析 FormData 请求
        Returns: 是否解析成功
        """
        try:
            log_info("请求解析", "开始解析 FormData 请求", 
                    details={"请求": req_data.request_id}, emoji="📥")
            
            form_data = await request.form()
            log_info("FormData获取", f"收到表单数据，字段数: {len(form_data)}", 
                    details={"请求": req_data.request_id})
            
            # 基础字段
            req_data.message = form_data.get("message", "")
            req_data.mode = form_data.get("mode", "banana")
            req_data.aspect_ratio = form_data.get("aspect_ratio")
            req_data.resolution = form_data.get("resolution")
            req_data.skip_optimization = form_data.get("skip_optimization") == "true"
            
            log_info("表单字段解析", f"message={len(req_data.message)}字符, mode={req_data.mode}", 
                    details={"请求": req_data.request_id}, emoji="📋")
            
            # 解析参考图片
            reference_images = form_data.getlist("reference_images")
            if reference_images:
                log_info("参考图片", f"检测到 {len(reference_images)} 个上传文件", 
                        details={"请求": req_data.request_id}, emoji="📸")
                req_data.reference_images = await FormDataParser._parse_images(
                    reference_images, req_data.request_id
                )
                log_info("参考图片", f"成功解析 {len(req_data.reference_images)} 张图片", 
                        details={"请求": req_data.request_id}, emoji="✅")
            
            return True
            
        except ValueError as ve:
            log_error("FormData解析失败", f"值错误: {str(ve)}", {"请求": req_data.request_id})
            return False
        except TypeError as te:
            log_error("FormData解析失败", f"类型错误: {str(te)}", {"请求": req_data.request_id})
            return False
        except Exception as e:
            log_error("FormData解析失败", f"未知错误: {str(e)} (类型: {type(e).__name__})", 
                     {"请求": req_data.request_id})
            import traceback
            log_error("完整堆栈", traceback.format_exc(), {"请求": req_data.request_id})
            return False
    
    @staticmethod
    async def _parse_images(upload_files: List[UploadFile], request_id: str) -> List[Image.Image]:
        """解析上传的图片文件为 PIL Image"""
        images = []
        for idx, file in enumerate(upload_files):
            try:
                log_info("图片处理", f"处理第{idx+1}张图片: {file.filename}", 
                        details={"请求": request_id}, emoji="🖼️")
                
                image_bytes = await file.read()
                size_kb = len(image_bytes) / 1024
                log_info("图片读取", f"第{idx+1}张完成, 大小: {size_kb:.1f}KB", 
                        details={"文件": file.filename, "请求": request_id})
                
                image = Image.open(io.BytesIO(image_bytes))
                log_info("图片打开", f"第{idx+1}张成功, 分辨率: {image.size}, 格式: {image.format}", 
                        details={"请求": request_id}, emoji="✅")
                
                images.append(image)
            except IOError as ie:
                log_warning("图片解析失败", f"第{idx+1}张 IO错误: {file.filename} - {str(ie)}", 
                           {"请求": request_id})
            except Exception as e:
                log_warning("图片解析失败", f"第{idx+1}张 未知错误: {file.filename} - {str(e)} ({type(e).__name__})", 
                           {"请求": request_id})
        
        log_info("图片处理完成", f"共处理 {len(upload_files)} 张，成功 {len(images)} 张", 
                details={"请求": request_id})
        return images


class JSONParser:
    """JSON 请求解析器"""
    
    @staticmethod
    async def parse(request: Request, req_data: BananaImageRequest) -> bool:
        """
        解析 JSON 请求（不支持参考图片）
        Returns: 是否解析成功
        """
        try:
            log_info("请求解析", "开始解析 JSON 请求", 
                    details={"请求": req_data.request_id}, emoji="📥")
            
            body = await request.json()
            log_info("JSON获取", f"成功解析 JSON，包含 {len(body)} 个字段", 
                    details={"请求": req_data.request_id})
            
            req_data.message = body.get("message", "")
            req_data.mode = body.get("mode", "banana")
            req_data.aspect_ratio = body.get("aspect_ratio")
            req_data.resolution = body.get("resolution")
            req_data.skip_optimization = body.get("skip_optimization", False)
            req_data.reference_images = []
            
            log_info("JSON字段解析", f"message={len(req_data.message)}字符, mode={req_data.mode}", 
                    details={"请求": req_data.request_id}, emoji="✅")
            
            return True
            
        except ValueError as ve:
            log_error("JSON解析失败", f"值错误: {str(ve)}", {"请求": req_data.request_id})
            return False
        except TypeError as te:
            log_error("JSON解析失败", f"类型错误: {str(te)}", {"请求": req_data.request_id})
            return False
        except Exception as e:
            log_error("JSON解析失败", f"未知错误: {str(e)} (类型: {type(e).__name__})", 
                     {"请求": req_data.request_id})
            import traceback
            log_error("完整堆栈", traceback.format_exc(), {"请求": req_data.request_id})
            return False


class ImageGenerator:
    """图像生成器 - 根据模式调用不同的生成器"""
    
    @staticmethod
    def generate(req_data: BananaImageRequest, 
                 gemini_2_5_func, 
                 gemini_3_func) -> Optional[Dict[str, Any]]:
        """
        根据模式生成图片
        
        Args:
            req_data: 请求数据
            gemini_2_5_func: Gemini 2.5 生成函数
            gemini_3_func: Gemini 3 生成函数
        
        Returns:
            图片数据字典或 None
        """
        mode_name = "Gemini 2.5 Flash" if req_data.mode == "banana" else "Gemini 3 Pro"
        ref_count = len(req_data.reference_images) if req_data.reference_images else 0
        
        log_info("开始生成", f"{mode_name} | 参考图: {ref_count}张", 
                details={
                    "提示词": req_data.message[:50] + "...",
                    "长宽比": req_data.aspect_ratio or "默认",
                    "分辨率": req_data.resolution or "默认",
                    "请求": req_data.request_id
                }, emoji="🎨")
        
        try:
            if req_data.mode == "banana":
                # Gemini 2.5: 1K, 最多3张参考图
                image_data = gemini_2_5_func(
                    prompt=req_data.message,
                    reference_images=req_data.reference_images if req_data.reference_images else None,
                    aspect_ratio=req_data.aspect_ratio
                )
            else:
                # Gemini 3 Pro: 4K, 最多14张参考图
                image_data = gemini_3_func(
                    prompt=req_data.message,
                    reference_images=req_data.reference_images if req_data.reference_images else None,
                    aspect_ratio=req_data.aspect_ratio,
                    image_size=req_data.resolution or "4K"
                )
            
            return image_data
            
        except Exception as e:
            log_error("生成失败", str(e), {"模式": mode_name, "请求": req_data.request_id})
            return None


class ResponseBuilder:
    """响应构建器"""
    
    @staticmethod
    def build_success_response(image_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """构建成功响应"""
        image_bytes = image_data.get("image_bytes")
        mime_type = image_data.get("mime_type", "image/jpeg")
        format_name = image_data.get("format", "jpeg")
        width = image_data.get("width", 0)
        height = image_data.get("height", 0)
        
        size_kb = len(image_bytes) / 1024 if image_bytes else 0
        log_success("生成完成", details={
            "大小": f"{size_kb:.1f}KB",
            "格式": format_name,
            "尺寸": f"{width}x{height}",
            "请求": request_id
        })
        
        return {
            "success": True,
            "image_bytes": image_bytes,
            "mime_type": mime_type,
            "format": format_name,
            "width": width,
            "height": height
        }
    
    @staticmethod
    def build_error_response(error_code: str, error_message: str, 
                            request_id: str, status_code: int = 500) -> Tuple[Dict[str, Any], int]:
        """构建错误响应"""
        log_error("请求失败", error_message, {"错误码": error_code, "请求": request_id})
        
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message
        }, status_code
    
    @staticmethod
    def handle_generator_error(image_data: Dict[str, Any], request_id: str) -> Tuple[Dict[str, Any], int]:
        """处理生成器返回的错误对象"""
        err_code = (image_data.get("error_code") or "UNKNOWN_ERROR").upper()
        
        # 映射 HTTP 状态码
        status_map = {
            "TIMEOUT_ERROR": 504,
            "PROXY_ERROR": 502,
            "API_ERROR": 502,
            "CHUNKED_ENCODING_ERROR": 502,
            "SAFETY_BLOCKED": 400,
            "CLIENT_CREATION_FAILED": 500,
            "MODULE_NOT_AVAILABLE": 500
        }
        status = status_map.get(err_code, 500)
        
        return ResponseBuilder.build_error_response(
            err_code,
            image_data.get("error_message", "未知错误"),
            request_id,
            status
        )


async def handle_banana_img_request(request: Request, 
                                     gemini_2_5_func, 
                                     gemini_3_func,
                                     force_mode: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
    """
    统一的 Banana Image 请求处理入口
    
    Args:
        request: FastAPI Request 对象
        gemini_2_5_func: Gemini 2.5 生成函数
        gemini_3_func: Gemini 3 生成函数
        force_mode: 强制使用的模式 ("banana" 或 "banana_pro")，若为 None 则从请求中读取
    
    Returns:
        (response_dict, status_code)
    """
    req_data = BananaImageRequest()
    
    # 1. 判断请求类型并解析
    content_type = request.headers.get("content-type", "").lower()
    is_form_data = "multipart/form-data" in content_type
    
    if is_form_data:
        success = await FormDataParser.parse(request, req_data)
    else:
        success = await JSONParser.parse(request, req_data)
    
    if not success:
        return ResponseBuilder.build_error_response(
            "PARSE_ERROR", "请求解析失败", req_data.request_id, 400
        )
    
    # 2. 如果指定了强制模式，则覆盖请求中的模式
    if force_mode:
        req_data.mode = force_mode
    
    # 3. 验证请求数据
    valid, error_msg = req_data.is_valid()
    if not valid:
        return ResponseBuilder.build_error_response(
            "INVALID_REQUEST", error_msg, req_data.request_id, 400
        )
    
    # 4. 调用生成器
    image_data = ImageGenerator.generate(req_data, gemini_2_5_func, gemini_3_func)
    
    if not image_data:
        return ResponseBuilder.build_error_response(
            "NO_IMAGE_DATA", "图片生成失败（无返回数据）", req_data.request_id
        )
    
    # 5. 检查是否是错误对象
    if isinstance(image_data, dict) and image_data.get("error"):
        return ResponseBuilder.handle_generator_error(image_data, req_data.request_id)
    
    # 6. 检查安全拦截
    if isinstance(image_data, str) and image_data.startswith("SAFETY_BLOCKED:"):
        error_message = image_data.replace("SAFETY_BLOCKED:", "").strip()
        return ResponseBuilder.build_error_response(
            "SAFETY_BLOCKED", error_message, req_data.request_id, 400
        )
    
    # 7. 验证返回格式
    if not isinstance(image_data, dict) or "image_bytes" not in image_data:
        return ResponseBuilder.build_error_response(
            "INVALID_FORMAT", "返回数据格式错误", req_data.request_id
        )
    
    image_bytes = image_data.get("image_bytes")
    if not image_bytes:
        return ResponseBuilder.build_error_response(
            "EMPTY_IMAGE_DATA", "图片数据为空", req_data.request_id
        )
    
    # 8. 验证图片数据类型（序列化检查）
    if not isinstance(image_bytes, bytes):
        log_error("序列化验证", f"image_bytes 类型不是 bytes: {type(image_bytes)}", 
                 {"请求": req_data.request_id})
        return ResponseBuilder.build_error_response(
            "SERIALIZATION_ERROR", 
            f"图片数据类型错误: 需要 bytes，实际为 {type(image_bytes)}", 
            req_data.request_id
        )
    
    log_success("数据验证", "所有返回数据已验证", {
        "图片大小": f"{len(image_bytes)} bytes",
        "MIME类型": image_data.get("mime_type"),
        "请求": req_data.request_id
    })
    
    # 9. 构建成功响应
    return ResponseBuilder.build_success_response(image_data, req_data.request_id), 200
