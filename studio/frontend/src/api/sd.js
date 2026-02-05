/**
 * SD3.5 图片生成 API
 * 使用 ComfyUI 接口进行图片生成
 */

// 日志工具：确保日志在浏览器控制台和终端都能看到
// 在浏览器环境中，console.log 会输出到浏览器控制台
// 在 Vite 开发环境中，代理日志会输出到终端
const logger = {
  log: (...args) => {
    console.log(...args);
  },
  error: (...args) => {
    console.error(...args);
  },
  group: (...args) => {
    console.group(...args);
  },
  groupEnd: () => {
    console.groupEnd();
  },
  warn: (...args) => {
    console.warn(...args);
  }
};

/**
 * 输出到终端的日志函数（使用 console.error 确保在终端可见）
 */
const logToTerminal = {
  request: (url, method, data = {}) => {
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`📤 [SD3.5前端] ${method} 请求 [${new Date().toISOString()}]`);
    console.error(`   请求 URL: ${url}`);
    Object.entries(data).forEach(([key, value]) => {
      console.error(`   ${key}: ${value}`);
    });
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  },
  response: (url, status, statusText, isError = false, data = '') => {
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    if (isError) {
      console.error(`❌ [SD3.5前端] 响应错误 [${new Date().toISOString()}]`);
    } else {
      console.error(`✅ [SD3.5前端] 响应成功 [${new Date().toISOString()}]`);
    }
    console.error(`   响应 URL: ${url}`);
    console.error(`   状态码: ${status} ${statusText}`);
    if (data) {
      const preview = typeof data === 'string' 
        ? data.substring(0, 300) + (data.length > 300 ? '...' : '')
        : JSON.stringify(data).substring(0, 300);
      console.error(`   响应数据: ${preview}`);
    }
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  },
  error: (type, url, message, suggestions = []) => {
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`❌ [SD3.5前端] ${type} [${new Date().toISOString()}]`);
    console.error(`   请求 URL: ${url}`);
    console.error(`   错误信息: ${message}`);
    if (suggestions.length > 0) {
      console.error('   ⚠️  可能原因:');
      suggestions.forEach((suggestion, index) => {
        console.error(`      ${index + 1}. ${suggestion}`);
      });
    }
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  }
};

// 从环境变量获取 SD3.5 API 地址
const getSD35ApiUrl = () => {
  // Vite 使用 import.meta.env 访问环境变量
  const apiUrl = import.meta.env.VITE_SD35_API_URL;
  
  if (apiUrl) {
    // 移除末尾的斜杠（如果有）
    return apiUrl.replace(/\/$/, '');
  }
  
  // 开发环境：使用 Vite 代理路径（避免 CORS 问题）
  // 生产环境：如果配置了环境变量则使用，否则使用代理路径
  if (import.meta.env.DEV) {
    // 开发环境使用代理路径
    return '/sd35';
  }
  
  // 生产环境默认使用代理路径（如果部署在同一服务器）
  // 或者需要配置环境变量指向实际的 SD3.5 服务器地址
  return '/sd35';
};

// 老照片修复服务器地址（环境变量优先，默认回退到现有公网地址）
const getOldPhotoApiUrl = () => {
  const apiUrl = import.meta.env.VITE_OLD_PHOTO_API_URL;

  if (apiUrl) {
    return apiUrl.replace(/\/$/, '');
  }

  // 回退到当前使用的公网地址，确保未配置环境变量时功能可用
  return 'https://u486297-8ceb-89b88d1b.westc.gpuhub.com:8443';
};

// 从环境变量获取 SD3.5 WebSocket 地址
const getSD35WsUrl = () => {
  const wsUrl = import.meta.env.VITE_SD35_WS_URL;
  
  if (wsUrl) {
    return wsUrl;
  }
  
  // 如果配置了 API URL 但没有配置 WS URL，从 API URL 推导
  const apiUrl = import.meta.env.VITE_SD35_API_URL;
  if (apiUrl) {
    // 将 https:// 转换为 wss://，http:// 转换为 ws://
    const wsUrl = apiUrl.replace(/^https?:\/\//, (match) => {
      return match === 'https://' ? 'wss://' : 'ws://';
    });
    // 确保末尾有 /ws
    return wsUrl.replace(/\/$/, '') + '/ws';
  }
  
  // 开发环境：使用 Vite 代理路径
  // Vite 的 proxy 配置中设置了 ws: true，会自动处理 WebSocket 代理
  if (import.meta.env.DEV) {
    // 开发环境：Vite 会自动将 ws://localhost:3000/sd35/ws 代理到远程服务器的 /ws
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/sd35/ws`;
  }
  
  // 生产环境：如果部署在同一服务器，使用相对路径
  // 如果需要连接到不同的服务器，需要在环境变量中配置 VITE_SD35_WS_URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/sd35/ws`;
};

const SD35_API_URL = getSD35ApiUrl();
const SD35_WS_URL = getSD35WsUrl();

// 输出配置信息（会在浏览器控制台显示）
logger.log('🔧 [SD3.5] API 配置:', {
  apiUrl: SD35_API_URL,
  wsUrl: SD35_WS_URL,
  env: import.meta.env.MODE,
  timestamp: new Date().toISOString()
});

/**
 * 上传图片到 SD3.5 服务器
 * @param {File} file - 图片文件
 * @param {string} type - 目录类型，可选值：'input'（默认）、'output'、'temp'
 * @param {string} subfolder - 子目录路径（可选）
 * @param {boolean} overwrite - 是否覆盖同名文件（可选，默认 false）
 * @returns {Promise<string>} 返回上传后的文件名
 */
export const uploadImage = async (file, type = 'input', subfolder = '', overwrite = false) => {
  try {
    const formData = new FormData();
    // ComfyUI 要求字段名必须是 'image'
    formData.append('image', file);
    
    // 添加可选参数
    if (type) {
      formData.append('type', type);
    }
    if (subfolder) {
      formData.append('subfolder', subfolder);
    }
    if (overwrite) {
      formData.append('overwrite', 'true');
    }
    
    // 构建上传 URL - 确保路径正确
    let uploadUrl;
    if (SD35_API_URL.startsWith('/')) {
      // 相对路径（通过代理）
      // 确保路径格式正确：/sd35/upload/image
      const basePath = SD35_API_URL.endsWith('/') ? SD35_API_URL.slice(0, -1) : SD35_API_URL;
      uploadUrl = `${basePath}/upload/image`;
    } else {
      // 绝对路径
      uploadUrl = `${SD35_API_URL.replace(/\/$/, '')}/upload/image`;
    }
    
    // 验证 URL 格式
    if (uploadUrl.includes('生图') || uploadUrl.includes('%E7%94%9F%E5%9B%BE')) {
      console.error('❌ [SD3.5] URL 构建错误：包含中文字符 "生图"');
      console.error(`   构建的 URL: ${uploadUrl}`);
      console.error(`   API 基础地址: ${SD35_API_URL}`);
      throw new Error('URL 构建错误：路径包含非法字符');
    }
    
    // 详细的请求日志（同时输出到控制台和终端）
    const logData = {
      uploadUrl,
      method: 'POST',
      fileName: file.name,
      fileSize: `${(file.size / 1024).toFixed(2)} KB`,
      fileType: file.type,
      type,
      subfolder: subfolder || '(空)',
      overwrite,
      apiBaseUrl: SD35_API_URL,
      corsMode: 'cors',
      credentials: 'omit',
      timestamp: new Date().toISOString()
    };
    
    console.group('📤 [SD3.5] 图片上传请求');
    console.log('📍 请求 URL:', uploadUrl);
    console.log('🔧 请求方法: POST');
    console.log('🌐 CORS 配置:', { mode: 'cors', credentials: 'omit' });
    console.log('📦 请求参数:', logData);
    console.log('🌐 API 基础地址:', SD35_API_URL);
    console.log('⏰ 请求时间:', new Date().toISOString());
    console.groupEnd();
    
    // 同时输出到终端
    logToTerminal.request(uploadUrl, 'POST', {
      'API 基础地址': SD35_API_URL,
      '文件名': file.name,
      '文件大小': `${(file.size / 1024).toFixed(2)} KB`,
      '文件类型': file.type,
      'CORS 模式': 'cors',
      'Credentials': 'omit (不发送)'
    });
    
    let response;
    let responseText = '';
    let responseHeaders = {};
    
    try {
      // 注意：不要手动设置 Content-Type，让浏览器自动设置（包括 boundary）
      // 配置 CORS：使用 mode: 'cors'，不发送 credentials 避免 403 错误
      response = await fetch(uploadUrl, {
        method: 'POST',
        mode: 'cors', // 明确启用 CORS 模式
        credentials: 'omit', // 不发送 credentials，防止触发 403 错误
        body: formData,
        // 不设置 Content-Type，让浏览器自动设置 multipart/form-data 和 boundary
      });
      
      // 读取响应头
      responseHeaders = Object.fromEntries(response.headers.entries());
      responseText = await response.text();
      
      // 详细的响应日志
      console.group(`📥 [SD3.5] 图片上传响应 (${response.status} ${response.statusText})`);
      console.log('📍 响应 URL:', response.url);
      console.log('📊 状态码:', response.status);
      console.log('📝 状态文本:', response.statusText);
      console.log('📋 响应头:', responseHeaders);
      console.log('📄 响应体长度:', `${(responseText.length / 1024).toFixed(2)} KB`);
      console.log('📄 响应体内容:', responseText.substring(0, 500) + (responseText.length > 500 ? '...' : ''));
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.response(
        response.url,
        response.status,
        response.statusText,
        !response.ok,
        responseText
      );
      
      if (!response.ok) {
        // 服务器返回错误（4xx, 5xx）
        console.group('❌ [SD3.5] 服务器返回错误');
        console.error('🔴 错误类型: 服务器端错误');
        console.error('📍 错误 URL:', response.url);
        console.error('📊 HTTP 状态码:', response.status);
        console.error('📝 HTTP 状态文本:', response.statusText);
        console.error('📋 响应头:', responseHeaders);
        console.error('📄 错误响应体:', responseText);
        console.error('💡 可能原因:');
        if (response.status === 403) {
          console.error('   - 服务器拒绝访问（权限问题）');
          console.error('   - 检查服务器 CORS 配置');
          console.error('   - 检查代理配置是否正确');
          console.error('   - 检查请求 URL 是否正确（应该是 /upload/image，不是 /生图）');
          console.error('   - 检查 ComfyUI 服务器是否正常运行');
        } else if (response.status === 404) {
          console.error('   - 接口路径不存在');
          console.error('   - 检查 URL 是否正确（应该是 /upload/image）');
          console.error('   - 检查 ComfyUI 服务器是否正常运行');
        } else if (response.status >= 500) {
          console.error('   - 服务器内部错误');
          console.error('   - 检查服务器日志');
        }
        console.groupEnd();
        
        // 同时输出到终端
        const suggestions = [];
        if (response.status === 403) {
          suggestions.push('请求路径错误（检查是否是 /upload/image，不是 /生图）');
          suggestions.push('ComfyUI 服务器权限配置问题');
          suggestions.push('代理配置问题（检查 vite.config.js 中的 /sd35 代理）');
          suggestions.push('ComfyUI 服务器未运行或地址错误');
          suggestions.push(`实际请求的 URL: ${response.url}`);
        } else if (response.status === 404) {
          suggestions.push('接口路径不存在（检查 URL 是否正确）');
          suggestions.push('ComfyUI 服务器未运行或地址错误');
        } else if (response.status >= 500) {
          suggestions.push('服务器内部错误');
          suggestions.push('检查服务器日志');
        }
        
        logToTerminal.error(
          '服务器错误',
          response.url,
          `${response.status} ${response.statusText}: ${responseText.substring(0, 200)}`,
          suggestions
        );
        
        throw new Error(`[服务器错误 ${response.status}] ${response.statusText}: ${responseText}`);
      }
      
      // 解析 JSON 响应
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        console.error('❌ [SD3.5] JSON 解析失败:', parseError);
        console.error('📄 原始响应:', responseText);
        throw new Error(`响应不是有效的 JSON: ${responseText.substring(0, 200)}`);
      }
      
      console.group('✅ [SD3.5] 图片上传成功');
      console.log('📦 返回数据:', data);
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.response(
        uploadUrl,
        response.status,
        response.statusText,
        false,
        JSON.stringify(data)
      );
      
      // 解析返回的文件名
      // ComfyUI 返回格式可能是：
      // - { name: "filename.png" }
      // - { filename: "filename.png" }
      // - 直接返回字符串 "filename.png"
      const filename = data?.name || data?.filename || data;
      
      // 如果返回的是对象但包含路径信息，提取文件名
      if (typeof filename === 'object' && filename?.name) {
        return filename.name;
      }
      
      return typeof filename === 'string' ? filename : String(filename);
      
    } catch (error) {
      // 网络错误或其他客户端错误
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        console.group('❌ [SD3.5] 网络请求失败');
        console.error('🔴 错误类型: 客户端网络错误');
        console.error('📍 请求 URL:', uploadUrl);
        console.error('📝 错误信息:', error.message);
        console.error('💡 可能原因:');
        console.error('   - 无法连接到服务器');
        console.error('   - 服务器未运行或地址错误');
        console.error('   - 网络连接问题');
        console.error('   - CORS 配置问题');
        console.error('   - 代理配置问题');
        console.groupEnd();
        
        // 同时输出到终端
        logToTerminal.error(
          '网络错误',
          uploadUrl,
          error.message,
          [
            'ComfyUI 服务器未运行（检查 localhost:6006）',
            'SSH 隧道未建立（如果使用隧道）',
            '代理配置问题（检查 vite.config.js）',
            '网络连接问题'
          ]
        );
        
        throw new Error(`[网络错误] 无法连接到 SD3.5 服务器 ${SD35_API_URL}: ${error.message}`);
      }
      
      // 如果是我们抛出的错误，直接重新抛出
      if (error.message?.includes('[服务器错误') || error.message?.includes('[网络错误]')) {
        throw error;
      }
      
      // 其他未知错误
      console.group('❌ [SD3.5] 未知错误');
      console.error('🔴 错误类型: 未知错误');
      console.error('📍 请求 URL:', uploadUrl);
      console.error('📝 错误信息:', error);
      console.error('📚 错误堆栈:', error.stack);
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.error(
        '未知错误',
        uploadUrl,
        error.message || String(error),
        []
      );
      
      throw error;
    }
  } catch (error) {
    // 外层 catch：处理所有未捕获的错误
    console.error('❌ [SD3.5] 图片上传失败:', error);
    
    // 提供更友好的错误信息
    if (error.message?.includes('403')) {
      throw new Error(`图片上传被拒绝（403）。请检查：1) SD3.5 服务器是否运行在 ${SD35_API_URL}；2) 服务器是否启用了 CORS；3) 代理配置是否正确。原始错误: ${error.message}`);
    } else if (error.message?.includes('CORS')) {
      throw new Error(`CORS 错误。请确保 Vite 代理配置正确，或 SD3.5 服务器启用了 CORS。原始错误: ${error.message}`);
    } else if (error.message?.includes('Failed to fetch') || error.message?.includes('NetworkError')) {
      throw new Error(`网络错误。无法连接到 SD3.5 服务器 ${SD35_API_URL}。请检查：1) 服务器是否运行；2) SSH 隧道是否建立（如果使用隧道）。原始错误: ${error.message}`);
    }
    
    throw error;
  }
};

/**
 * 构建 SD3.5 的 prompt JSON
 * @param {string} prompt - 提示词
 * @param {string} negativePrompt - 负面提示词（可选）
 * @param {number} width - 图片宽度
 * @param {number} height - 图片高度
 * @param {string} uploadedImageName - 上传的参考图片文件名（可选，用于图生图）
 * @param {number} seed - 随机种子（可选）
 * @param {number} steps - 采样步数（可选，默认4）
 * @param {number} cfg - CFG scale（可选，默认1.0）
 * @param {number} denoise - 去噪强度（可选，默认1.0，用于图生图）
 * @returns {Object} prompt JSON 对象
 */
export const buildPromptJSON = ({
  prompt,
  negativePrompt = 'low quality',
  width = 1024,
  height = 1024,
  uploadedImageName = null,
  uploadedImageNames = null, // ⚠️ 新增：支持多张参考图片（用于合影场景）
  seed = null,
  steps = 4,
  cfg = 1.0,
  denoise = 1.0,
  enableFaceID = true, // ⚠️ 新增：是否启用 FaceID 保持功能（默认启用）
  enableControlNet = true, // ⚠️ 新增：是否启用 ControlNet（默认启用）
  enableFaceDetailer = true, // ⚠️ 新增：是否启用面部修复（默认启用）
}) => {
  // 生成随机种子（如果未提供）
  const finalSeed = seed !== null ? seed : Math.floor(Math.random() * 1000000);
  
  const promptJSON = {
    "1": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": {
        "ckpt_name": "sd3.5_large_turbo.safetensors"
      }
    },
    "2": {
      "class_type": "TripleCLIPLoader",
      "inputs": {
        "clip_name1": "clip_l.safetensors",
        "clip_name2": "clip_g.safetensors",
        "clip_name3": "t5xxl_fp16.safetensors"
      }
    },
    "3": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": prompt,
        "clip": ["2", 0]
      }
    },
    "4": {
      "class_type": "EmptyLatentImage",
      "inputs": {
        "width": width,
        "height": height,
        "batch_size": 1
      }
    },
    "5": {
      "class_type": "KSampler",
      "inputs": {
        "seed": finalSeed,
        "steps": steps,
        "cfg": cfg,
        "sampler_name": "euler",
        "scheduler": "simple",
        "denoise": denoise,
        "model": ["1", 0],
        "positive": ["3", 0],
        "negative": ["6", 0],
        "latent_image": ["4", 0]  // ⚠️ 初始连接到 EmptyLatentImage (节点 4)，如果有参考图片，后面会更新为 VAEEncode (节点 10)
      }
    },
    "6": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": negativePrompt,
        "clip": ["2", 0]
      }
    },
    "7": {
      "class_type": "VAEDecode",
      "inputs": {
        "samples": ["5", 0],
        "vae": ["1", 2]
      }
    },
    "8": {
      "class_type": "SaveImage",
      "inputs": {
        "filename_prefix": "SD35_",
        "images": ["7", 0]
      }
    }
  };
  
  // ⚠️ 处理参考图片：支持单张或多张（合影场景）
  const referenceImages = uploadedImageNames && uploadedImageNames.length > 0 
    ? uploadedImageNames 
    : (uploadedImageName ? [uploadedImageName] : []);
  const hasReferenceImages = referenceImages.length > 0;
  const primaryImageName = referenceImages.length > 0 ? referenceImages[0] : null;
  
  // ⚠️ 商业级 FaceID 保持工作流
  // 如果有参考图片，添加 LoadImage、VAEEncode 和 FaceID 相关节点
  if (hasReferenceImages) {
    console.group('🖼️ [SD3.5] 构建商业级 FaceID 保持工作流');
    console.log('📸 参考图片数量:', referenceImages.length);
    console.log('📁 参考图片文件名:', referenceImages);
    console.log('🎯 启用 FaceID:', enableFaceID);
    console.log('🎯 启用 ControlNet:', enableControlNet);
    console.log('🎯 启用面部修复:', enableFaceDetailer);
    console.groupEnd();
    
    let nextNodeId = 9;
    let lastImageOutput = null;
    let lastLatentOutput = null;
    
    // 1. 加载所有参考图片（ID 9+）
    const imageLoadNodes = {};
    referenceImages.forEach((imageName, index) => {
      const nodeId = String(nextNodeId++);
      imageLoadNodes[nodeId] = {
        "class_type": "LoadImage",
        "inputs": {
          "image": imageName
        }
      };
      promptJSON[nodeId] = imageLoadNodes[nodeId];
      lastImageOutput = [nodeId, 0];
    });
    
    // 2. VAEEncode 将第一张图片转换为 Latent（用于 Img2Img）
    const vaeEncodeNodeId = String(nextNodeId++);
    promptJSON[vaeEncodeNodeId] = {
      "class_type": "VAEEncode",
      "inputs": {
        "pixels": [String(Object.keys(imageLoadNodes)[0]), 0],
        "vae": ["1", 2]
      }
    };
    lastLatentOutput = [vaeEncodeNodeId, 0];
    
    // 3. 更新 KSampler 的 latent_image 输入（Img2Img 模式）
    promptJSON["5"].inputs.latent_image = lastLatentOutput;
    
    // 4. IP-Adapter-FaceID 工作流（如果启用）
    if (enableFaceID && hasReferenceImages) {
      console.group('🎯 [SD3.5] 构建 IP-Adapter-FaceID 工作流');
      console.log('📸 参考图片数量:', referenceImages.length);
      console.log('📁 参考图片文件名:', referenceImages);
      
      // 4.1 加载 CLIP Vision（IP-Adapter 需要）
      const clipVisionLoaderId = String(nextNodeId++);
      promptJSON[clipVisionLoaderId] = {
        "class_type": "CLIPVisionLoader",
        "inputs": {
          "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
        }
      };
      
      // 4.2 加载 IP-Adapter 模型 (ip-adapter-faceid_sdxl.bin)
      // ⚠️ 注意：使用 IPAdapterUnifiedLoader 而不是 IPAdapterModelLoader
      const ipAdapterUnifiedLoaderId = String(nextNodeId++);
      promptJSON[ipAdapterUnifiedLoaderId] = {
        "class_type": "IPAdapterUnifiedLoader",
        "inputs": {
          "preset": "PLUS (high strength)",
          "ipadapter_file": "ip-adapter-faceid_sdxl.bin",
          "clip_vision": [clipVisionLoaderId, 0],
          "model": ["1", 0]
        }
      };
      console.log('✅ [SD3.5] 添加 IPAdapterUnifiedLoader 节点 (ID: ' + ipAdapterUnifiedLoaderId + ', 模型: ip-adapter-faceid_sdxl.bin)');
      
      // 4.2 检测图片数量，决定使用单图模式还是双人合影模式
      const imageCount = referenceImages.length;
      const imageNodeIds = Object.keys(imageLoadNodes).sort((a, b) => parseInt(a) - parseInt(b));
      
      if (imageCount === 2) {
        // ⚠️ 双人合影模式：生成两个 IPAdapterAdvanced 节点 + ConditioningSetMask
        console.log('👥 [SD3.5] 检测到 2 张参考图片，启用双人合影模式');
        
        const firstImageNodeId = imageNodeIds[0];
        const secondImageNodeId = imageNodeIds[1];
        
        // 4.2.1 第一个 IPAdapterAdvanced（对应左区域，绑定第一张图片）
        // ⚠️ 注意：根据参考 JSON，IPAdapterAdvanced 只需要 weight, model, ipadapter, image 参数
        const ipAdapter1Id = String(nextNodeId++);
        promptJSON[ipAdapter1Id] = {
          "class_type": "IPAdapterAdvanced",
          "inputs": {
            "weight": 0.75,  // ⚠️ 权重控制：0.75
            "model": ["1", 0],
            "ipadapter": [ipAdapterUnifiedLoaderId, 1],  // IPAdapterUnifiedLoader 的输出索引 1
            "image": [firstImageNodeId, 0]
          }
        };
        console.log('✅ [SD3.5] 添加第一个 IPAdapterAdvanced 节点 (ID: ' + ipAdapter1Id + ', 对应左区域, weight=0.75)');
        
        // 4.2.2 第二个 IPAdapterAdvanced（对应右区域，绑定第二张图片）
        // ⚠️ 注意：第二个 IPAdapterAdvanced 的 model 输入连接到第一个的输出
        const ipAdapter2Id = String(nextNodeId++);
        promptJSON[ipAdapter2Id] = {
          "class_type": "IPAdapterAdvanced",
          "inputs": {
            "weight": 0.75,  // ⚠️ 权重控制：0.75
            "model": [ipAdapter1Id, 0],  // 连接到第一个 IPAdapterAdvanced 的 model 输出
            "ipadapter": [ipAdapterUnifiedLoaderId, 1],  // IPAdapterUnifiedLoader 的输出索引 1
            "image": [secondImageNodeId, 0]
          }
        };
        console.log('✅ [SD3.5] 添加第二个 IPAdapterAdvanced 节点 (ID: ' + ipAdapter2Id + ', 对应右区域, weight=0.75)');
        
        // 4.2.3 ConditioningSetArea - 左区域（绑定第一张图片的特征）
        // ⚠️ 注意：使用 ConditioningSetArea 而不是 ConditioningSetMask + MaskFromRegion
        // 左区域：(0,0,512,1024)
        const conditioningSetArea1Id = String(nextNodeId++);
        promptJSON[conditioningSetArea1Id] = {
          "class_type": "ConditioningSetArea",
          "inputs": {
            "width": Math.floor(width / 2),  // 512
            "height": height,  // 1024
            "x": 0,
            "y": 0,
            "strength": 1.0,
            "conditioning": ["3", 0]  // 使用原始的 CLIPTextEncode 输出
          }
        };
        
        // 4.2.4 ConditioningSetArea - 右区域（绑定第二张图片的特征）
        // 右区域：(512,0,512,1024)
        const conditioningSetArea2Id = String(nextNodeId++);
        promptJSON[conditioningSetArea2Id] = {
          "class_type": "ConditioningSetArea",
          "inputs": {
            "width": Math.floor(width / 2),  // 512
            "height": height,  // 1024
            "x": Math.floor(width / 2),  // 512
            "y": 0,
            "strength": 1.0,
            "conditioning": ["3", 0]  // 使用原始的 CLIPTextEncode 输出
          }
        };
        console.log('✅ [SD3.5] 添加 ConditioningSetArea 节点 (左区域: ' + conditioningSetArea1Id + ', 右区域: ' + conditioningSetArea2Id + ')');
        
        // 4.2.5 合并两个 ConditioningSetArea 的输出
        const conditioningCombineId = String(nextNodeId++);
        promptJSON[conditioningCombineId] = {
          "class_type": "ConditioningCombine",
          "inputs": {
            "conditioning_1": [conditioningSetArea1Id, 0],
            "conditioning_2": [conditioningSetArea2Id, 0]
          }
        };
        
        // 4.2.6 更新 KSampler 的 positive 输入，连接到合并后的 conditioning
        // 同时更新 model 输入，连接到第二个 IPAdapterAdvanced 的 model 输出（链式连接）
        promptJSON["5"].inputs.positive = [conditioningCombineId, 0];
        promptJSON["5"].inputs.model = [ipAdapter2Id, 0];  // 使用第二个 IPAdapterAdvanced 的 model 输出（链式连接）
        
        console.log('✅ [SD3.5] 连接 KSampler 到 ConditioningCombine (ID: ' + conditioningCombineId + ')');
        console.log('✅ [SD3.5] 双人合影模式配置完成：左区域绑定图1，右区域绑定图2');
        
      } else if (imageCount === 1) {
        // 单图模式：使用单个 IPAdapterAdvanced
        console.log('👤 [SD3.5] 检测到 1 张参考图片，启用单图模式');
        
        const firstImageNodeId = imageNodeIds[0];
        const ipAdapterId = String(nextNodeId++);
        promptJSON[ipAdapterId] = {
          "class_type": "IPAdapterAdvanced",
          "inputs": {
            "weight": 0.75,  // ⚠️ 权重控制：0.75
            "model": ["1", 0],
            "ipadapter": [ipAdapterUnifiedLoaderId, 1],  // IPAdapterUnifiedLoader 的输出索引 1
            "image": [firstImageNodeId, 0]
          }
        };
        
        // 更新 KSampler 的 model 输入（positive 保持原样，使用节点 3）
        promptJSON["5"].inputs.model = [ipAdapterId, 0];
        
        console.log('✅ [SD3.5] 添加 IPAdapterAdvanced 节点 (ID: ' + ipAdapterId + ', weight=0.75)');
      } else {
        console.warn('⚠️ [SD3.5] 参考图片数量为 ' + imageCount + '，暂不支持，仅使用第一张图片');
        // 使用第一张图片，回退到单图模式逻辑
        const firstImageNodeId = imageNodeIds[0];
        const ipAdapterId = String(nextNodeId++);
        promptJSON[ipAdapterId] = {
          "class_type": "IPAdapterAdvanced",
          "inputs": {
            "weight": 0.75,
            "model": ["1", 0],
            "ipadapter": [ipAdapterUnifiedLoaderId, 1],  // IPAdapterUnifiedLoader 的输出索引 1
            "image": [firstImageNodeId, 0]
          }
        };
        promptJSON["5"].inputs.model = [ipAdapterId, 0];
      }
      
      console.groupEnd();
    }
    
    // 5. ControlNet (Canny/Depth) - 如果启用
    if (enableControlNet && primaryImageName) {
      // 使用第一张参考图片作为 ControlNet 输入
      const firstImageNodeId = String(Object.keys(imageLoadNodes)[0]);
      
      // 使用 Canny 边缘检测提取轮廓
      const cannyPreprocessorNodeId = String(nextNodeId++);
      promptJSON[cannyPreprocessorNodeId] = {
        "class_type": "CannyEdgePreprocessor",
        "inputs": {
          "image": [firstImageNodeId, 0],
          "low_threshold": 100,
          "high_threshold": 200
        }
      };
      
      // 注意：ControlNet 的完整连接还需要 ControlNetLoader 和 ControlNetApplyAdvanced 节点
      // 这里仅展示基础结构（Canny 预处理器），实际实现需要根据服务器的 ComfyUI 配置调整
      // TODO: 添加 ControlNetLoader 和 ControlNetApplyAdvanced 节点，连接到 KSampler
      console.log('✅ [SD3.5] 添加 ControlNet (Canny) 预处理器节点 (ID: ' + cannyPreprocessorNodeId + ')');
      console.log('   ⚠️ 注意：完整的 ControlNet 工作流还需要 ControlNetLoader 和 ControlNetApplyAdvanced 节点');
    }
    
    // 6. 更新 VAEDecode 的输出连接（如果有面部修复，连接到 Adetailer）
    let finalImageOutput = ["7", 0];
    
    // 7. Adetailer 面部修复（如果启用）
    if (enableFaceDetailer) {
      const adetailerNodeId = String(nextNodeId++);
      try {
        promptJSON[adetailerNodeId] = {
          "class_type": "ADetailer",
          "inputs": {
            "image": ["7", 0], // 从 VAEDecode 接收
            "model": ["1", 0],
            "clip": ["2", 0],
            "vae": ["1", 2],
            "positive": ["3", 0],
            "negative": ["6", 0]
          }
        };
        finalImageOutput = [adetailerNodeId, 0];
        console.log('✅ [SD3.5] 添加 Adetailer 面部修复节点 (ID: ' + adetailerNodeId + ')');
      } catch (e) {
        console.warn('⚠️ [SD3.5] Adetailer 节点不可用，使用基础输出');
      }
    }
    
    // 8. 更新 SaveImage 连接到最终输出
    promptJSON["8"].inputs.images = finalImageOutput;
    
    // 9. 多图模式：ConditioningSetMask（分区域引导）- 如果有两张或更多图片
    if (referenceImages.length >= 2 && enableFaceID) {
      console.log('📋 [SD3.5] 多图模式：准备添加 ConditioningSetMask 节点（分区域引导）');
      // 注意：ConditioningSetMask 需要手动定义区域和提示词，这里仅作为框架
      // 实际实现需要根据具体需求定义左侧/右侧区域和对应的提示词
      // 节点 ID 预留为 nextNodeId++
      // TODO: 实现 ConditioningSetMask 节点，支持分区域引导（左边区域参考图A，右边区域参考图B）
    }
    
    console.group('✅ [SD3.5] 商业级 FaceID 工作流构建完成');
    console.log('📦 节点总数:', Object.keys(promptJSON).length);
    console.log('📸 参考图片数量:', referenceImages.length);
    console.log('🎯 FaceID 启用:', enableFaceID);
    console.log('🎯 ControlNet 启用:', enableControlNet);
    console.log('🎯 面部修复启用:', enableFaceDetailer);
    console.groupEnd();
  }
  
  // 输出完整的 prompt JSON 结构
  console.group('📋 [SD3.5] Prompt JSON 结构');
  console.log('📦 节点数量:', Object.keys(promptJSON).length);
  console.log('🔢 节点 ID 列表:', Object.keys(promptJSON).sort((a, b) => parseInt(a) - parseInt(b)));
  console.log('📄 完整 JSON:', JSON.stringify(promptJSON, null, 2));
  console.groupEnd();
  
  return promptJSON;
};

/**
 * 提交 prompt 到 SD3.5 服务器
 * @param {Object} promptJSON - prompt JSON 对象
 * @returns {Promise<string>} 返回 prompt_id
 */
/**
 * 提交 Prompt 到 SD3.5 服务器（文生图）
 */
export const submitPromptForTextToImage = async (promptJSON) => {
  const SD35_API_URL = getSD35ApiUrl();
  // 确保 URL 格式正确：移除末尾斜杠，然后添加 /prompt
  const baseUrl = SD35_API_URL.replace(/\/$/, '');
  const promptUrl = `${baseUrl}/prompt`;
  
  console.group('📤 [SD3.5文生图] 提交 Prompt 请求');
  console.log('📍 请求 URL:', promptUrl);
  console.log('🌐 API 基础地址:', SD35_API_URL);
  console.log('🌐 处理后的基础地址:', baseUrl);
  console.log('📦 Prompt 节点数:', Object.keys(promptJSON).length);
  console.groupEnd();
  
  return await submitPromptInternal(promptJSON, promptUrl, '文生图');
};

/**
 * 提交 Prompt 到 SD3.5 服务器（生成合影）
 */
export const submitPromptForGroupPhoto = async (promptJSON) => {
  const SD35_API_URL = getSD35ApiUrl();
  // 确保 URL 格式正确：移除末尾斜杠，然后添加 /prompt
  const baseUrl = SD35_API_URL.replace(/\/$/, '');
  const promptUrl = `${baseUrl}/prompt`;
  
  console.group('📤 [SD3.5合影] 提交 Prompt 请求');
  console.log('📍 请求 URL:', promptUrl);
  console.log('🌐 API 基础地址:', SD35_API_URL);
  console.log('🌐 处理后的基础地址:', baseUrl);
  console.log('📦 Prompt 节点数:', Object.keys(promptJSON).length);
  console.groupEnd();
  
  return await submitPromptInternal(promptJSON, promptUrl, '生成合影');
};

/**
 * 提交 Prompt 到老照片修复服务器
 */
export const submitPromptForOldPhoto = async (promptJSON) => {
  const OLD_PHOTO_API_URL = getOldPhotoApiUrl();
  // 确保 URL 格式正确：移除末尾斜杠，然后添加 /prompt
  const baseUrl = OLD_PHOTO_API_URL.replace(/\/$/, '');
  const promptUrl = `${baseUrl}/prompt`;
  
  console.group('📤 [老照片修复] 提交 Prompt 请求');
  console.log('📍 请求 URL:', promptUrl);
  console.log('🌐 API 基础地址:', OLD_PHOTO_API_URL);
  console.log('🌐 处理后的基础地址:', baseUrl);
  console.log('📦 Prompt 节点数:', Object.keys(promptJSON).length);
  console.groupEnd();
  
  return await submitPromptInternal(promptJSON, promptUrl, '老照片修复');
};

/**
 * 内部函数：提交 Prompt 的通用逻辑
 */
const submitPromptInternal = async (promptJSON, promptUrl, functionName = 'SD3.5') => {
  const requestBody = { prompt: promptJSON };
  const requestBodyStr = JSON.stringify(requestBody, null, 2); // 格式化 JSON，便于阅读
  
  // 详细的请求日志
  console.group(`📤 [${functionName}] 提交 Prompt 请求`);
  console.log('📍 请求 URL:', promptUrl);
  console.log('🔧 请求方法: POST');
  console.log('📦 Prompt 节点数:', Object.keys(promptJSON).length);
  console.log('📄 请求体大小:', `${(requestBodyStr.length / 1024).toFixed(2)} KB`);
  console.log('⏰ 请求时间:', new Date().toISOString());
  console.log('');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📋 完整 JSON 负载:');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(requestBodyStr);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.groupEnd();
  
  // 同时输出到终端
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.error(`📤 [${functionName}前端] 提交 Prompt 请求 [${new Date().toISOString()}]`);
  console.error(`   请求 URL: ${promptUrl}`);
  console.error(`   Prompt 节点数: ${Object.keys(promptJSON).length}`);
  console.error(`   请求体大小: ${(requestBodyStr.length / 1024).toFixed(2)} KB`);
  console.error('');
  console.error('📋 完整 JSON 负载:');
  console.error(requestBodyStr);
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  let response;
  let responseText = '';
  let responseHeaders = {};
  
  try {
    // 配置 CORS：使用 mode: 'cors'，不发送 credentials 避免 403 错误
    response = await fetch(promptUrl, {
      method: 'POST',
      mode: 'cors', // 明确启用 CORS 模式
      credentials: 'omit', // 不发送 credentials，防止触发 403 错误
      headers: {
        'Content-Type': 'application/json',
      },
      body: requestBodyStr,
    });
    
    // 读取响应头
    responseHeaders = Object.fromEntries(response.headers.entries());
    responseText = await response.text();
    
    // 详细的响应日志
    console.group(`📥 [${functionName}] Prompt 提交响应 (${response.status} ${response.statusText})`);
    console.log('📍 响应 URL:', response.url);
    console.log('📊 状态码:', response.status);
    console.log('📝 状态文本:', response.statusText);
    console.log('📋 响应头:', responseHeaders);
    console.log('📄 响应体长度:', `${(responseText.length / 1024).toFixed(2)} KB`);
    console.log('');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📄 完整响应体内容:');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(responseText);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`📥 [${functionName}前端] Prompt 提交响应 [${new Date().toISOString()}]`);
    console.error(`   状态码: ${response.status} ${response.statusText}`);
    console.error(`   响应体长度: ${(responseText.length / 1024).toFixed(2)} KB`);
    console.error('');
    console.error('📄 完整响应体内容:');
    console.error(responseText);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    if (!response.ok) {
      // 服务器返回错误
      console.group(`❌ [${functionName}] 服务器返回错误`);
      console.error('🔴 错误类型: 服务器端错误');
      console.error('📍 错误 URL:', response.url);
      console.error('📊 HTTP 状态码:', response.status);
      console.error('📝 HTTP 状态文本:', response.statusText);
      console.error('📋 响应头:', responseHeaders);
      console.error('');
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error('📄 完整错误响应体:');
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error(responseText);
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error('💡 可能原因:');
      const suggestions = [];
      if (response.status === 400) {
        console.error('   - Prompt JSON 格式错误');
        console.error('   - 检查 prompt 结构是否正确');
        suggestions.push('Prompt JSON 格式错误');
        suggestions.push('检查 prompt 结构是否正确');
      } else if (response.status === 403) {
        console.error('   - 服务器拒绝访问（权限问题）');
        suggestions.push('服务器拒绝访问（权限问题）');
      } else if (response.status === 404) {
        console.error('   - 接口不存在（404）');
        console.error('   - 检查服务器地址是否正确');
        console.error('   - 检查接口路径是否正确');
        suggestions.push('接口不存在（404）');
        suggestions.push('检查服务器地址和接口路径');
      } else if (response.status === 500) {
        console.error('   - 服务器内部错误');
        console.error('   - 检查服务器日志');
        suggestions.push('服务器内部错误');
        suggestions.push('检查服务器日志');
      }
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.error(
        '服务器错误',
        response.url,
        `${response.status} ${response.statusText}: ${responseText.substring(0, 200)}`,
        suggestions
      );
      
      throw new Error(`[${functionName}服务器错误 ${response.status}] ${response.statusText}: ${responseText}`);
    }
    
    // 解析 JSON 响应
    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      console.error('❌ [SD3.5] JSON 解析失败:', parseError);
      console.error('📄 原始响应:', responseText);
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error(`❌ [SD3.5前端] JSON 解析失败 [${new Date().toISOString()}]`);
      console.error(`   解析错误: ${parseError.message}`);
      console.error(`   原始响应: ${responseText}`);
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      throw new Error(`响应不是有效的 JSON: ${responseText.substring(0, 200)}`);
    }
    
    console.group(`✅ [${functionName}] Prompt 提交成功`);
    console.log('📦 返回数据:', data);
    console.log('📦 返回数据类型:', typeof data);
    console.log('📦 返回数据键:', Object.keys(data));
    const promptId = data.prompt_id || data;
    console.log('🆔 Prompt ID:', promptId);
    console.log('🆔 Prompt ID 类型:', typeof promptId);
    console.log('🆔 Prompt ID 值:', JSON.stringify(promptId));
    
    // 验证 prompt_id 是否存在
    if (!promptId || promptId === 'undefined' || promptId === undefined) {
      console.error('❌ [SD3.5] 警告：Prompt ID 无效！');
      console.error('📦 完整返回数据:', JSON.stringify(data, null, 2));
      console.error('💡 可能原因:');
      console.error('   - 服务器返回格式不正确');
      console.error('   - Prompt JSON 格式错误');
      console.error('   - 服务器处理失败');
    }
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`✅ [SD3.5前端] Prompt 提交成功 [${new Date().toISOString()}]`);
    console.error(`   状态码: ${response.status}`);
    console.error(`   Prompt ID: ${promptId}`);
    console.error(`   Prompt ID 类型: ${typeof promptId}`);
    console.error(`   完整返回数据: ${JSON.stringify(data, null, 2)}`);
    if (!promptId || promptId === 'undefined' || promptId === undefined) {
      console.error('   ⚠️  警告：Prompt ID 无效！');
    }
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    // 如果 prompt_id 无效，抛出错误
    if (!promptId || promptId === 'undefined' || promptId === undefined) {
      throw new Error(`服务器返回的 Prompt ID 无效。返回数据: ${JSON.stringify(data)}`);
    }
    
    // ComfyUI 返回格式通常是 { prompt_id: "xxx" }
    return promptId;
    
  } catch (error) {
    // 网络错误或其他客户端错误
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      console.group('❌ [SD3.5] 网络请求失败');
      console.error('🔴 错误类型: 客户端网络错误');
      console.error('📍 请求 URL:', promptUrl);
      console.error('📝 错误信息:', error.message);
      console.error('💡 可能原因:');
      console.error('   - 无法连接到服务器');
      console.error('   - 服务器未运行或地址错误');
      console.error('   - 网络连接问题');
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.error(
        '网络错误',
        promptUrl,
        error.message,
        [
          '无法连接到服务器',
          '服务器未运行或地址错误',
          '网络连接问题'
        ]
      );
      
      throw new Error(`[网络错误] 无法连接到 SD3.5 服务器 ${SD35_API_URL}: ${error.message}`);
    }
    
    // 如果是我们抛出的错误，直接重新抛出
    if (error.message.includes('[服务器错误') || error.message.includes('[网络错误]')) {
      throw error;
    }
    
    // 其他未知错误
    console.group('❌ [SD3.5] 未知错误');
    console.error('🔴 错误类型: 未知错误');
    console.error('📍 请求 URL:', promptUrl);
    console.error('📝 错误信息:', error);
    console.error('📚 错误堆栈:', error.stack);
    console.groupEnd();
    throw error;
  }
};

/**
 * 通过 WebSocket 监听任务进度
 * @param {string} promptId - prompt ID
 * @param {Function} onProgress - 进度回调函数 (progress) => void
 * @param {Function} onComplete - 完成回调函数 (imageFilename) => void
 * @param {Function} onError - 错误回调函数 (error) => void
 * @param {number} timeout - 超时时间（毫秒），默认 5 分钟
 * @returns {Promise<string>} 返回生成的图片文件名
 */
export const watchProgress = (promptId, onProgress, onComplete, onError, timeout = 5 * 60 * 1000) => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const timeoutMs = timeout;
    
    console.group('🔌 [SD3.5] WebSocket 连接');
    console.log('📍 WebSocket URL:', SD35_WS_URL);
    console.log('🆔 Prompt ID:', promptId);
    console.log('⏰ 连接时间:', new Date().toISOString());
    console.log('⏱️ 超时设置:', `${timeoutMs / 1000} 秒 (${timeoutMs / 60000} 分钟)`);
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`🔌 [SD3.5前端] WebSocket 连接开始 [${new Date().toISOString()}]`);
    console.error(`   WebSocket URL: ${SD35_WS_URL}`);
    console.error(`   Prompt ID: ${promptId}`);
    console.error(`   超时设置: ${timeoutMs / 1000} 秒`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    const ws = new WebSocket(SD35_WS_URL);
    let isResolved = false;
    let timeoutTimer = null;
    let heartbeatTimer = null;
    let lastMessageTime = Date.now();
    let messageCount = 0;
    
    // 设置超时定时器
    timeoutTimer = setTimeout(() => {
      if (!isResolved) {
        isResolved = true;
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        const error = new Error(`[超时错误] 任务执行超时（${elapsed} 秒），Prompt ID: ${promptId}`);

        // 简化日志：默认输出一行关键错误，详细内容仅在开发或显式开启时打印
        console.error('⏰ [SD3.5] WebSocket 超时', {
          promptId,
          elapsed: `${elapsed} 秒`,
          messageCount,
          lastMessageISO: lastMessageTime > 0 ? new Date(lastMessageTime).toISOString() : '无'
        });

        // 详细诊断仅在开发或开启 verbose 日志时输出
        const verbose = (import.meta?.env?.VITE_LOG_VERBOSE ?? import.meta?.env?.DEV) === true ||
                        (import.meta?.env?.VITE_LOG_VERBOSE === 'true');
        if (verbose) {
          console.group('⏰ [SD3.5] WebSocket 超时（详细）');
          console.error('🔴 错误类型: 任务执行超时');
          console.error('🆔 Prompt ID:', promptId);
          console.error('⏱️ 已等待时间:', `${elapsed} 秒`);
          console.error('📊 收到消息数:', messageCount);
          console.error('💡 可能原因:');
          console.error('   - 服务器处理时间过长');
          console.error('   - WebSocket 连接中断');
          console.error('   - 任务执行失败但未返回错误');
          console.error('   - 网络连接问题');
          console.groupEnd();

          // 同步到终端的分隔块也只在 verbose 下输出
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          console.error(`⏰ [SD3.5前端] 任务超时 [${new Date().toISOString()}]`);
          console.error(`   Prompt ID: ${promptId}`);
          console.error(`   已等待: ${elapsed} 秒`);
          console.error(`   收到消息数: ${messageCount}`);
          console.error(`   最后消息时间: ${lastMessageTime > 0 ? new Date(lastMessageTime).toISOString() : '无'}`);
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        }
        
        ws.close();
        if (onError) onError(error);
        reject(error);
      }
    }, timeoutMs);
    
    // 心跳检查：每 30 秒检查一次是否还有消息
    heartbeatTimer = setInterval(() => {
      if (!isResolved) {
        const timeSinceLastMessage = Date.now() - lastMessageTime;
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        console.log(`💓 [SD3.5] 心跳检查 - 已等待 ${elapsed} 秒，收到 ${messageCount} 条消息，距离上次消息 ${(timeSinceLastMessage / 1000).toFixed(2)} 秒`);
        
        // 如果超过 2 分钟没有收到任何消息，发出警告
        if (timeSinceLastMessage > 2 * 60 * 1000 && lastMessageTime > 0) {
          console.warn('⚠️ [SD3.5] 警告：超过 2 分钟未收到 WebSocket 消息');
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          console.error(`⚠️ [SD3.5前端] 长时间无消息 [${new Date().toISOString()}]`);
          console.error(`   Prompt ID: ${promptId}`);
          console.error(`   已等待: ${elapsed} 秒`);
          console.error(`   距离上次消息: ${(timeSinceLastMessage / 1000).toFixed(2)} 秒`);
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        }
      } else {
        clearInterval(heartbeatTimer);
      }
    }, 30 * 1000);
    
    ws.onopen = () => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
      console.group('✅ [SD3.5] WebSocket 连接已建立');
      console.log('📍 WebSocket URL:', SD35_WS_URL);
      console.log('🆔 Prompt ID:', promptId);
      console.log('📊 连接状态:', ws.readyState === WebSocket.OPEN ? 'OPEN' : ws.readyState);
      console.log('⏱️ 连接耗时:', `${elapsed} 秒`);
      console.groupEnd();
      
      // 同时输出到终端
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error(`✅ [SD3.5前端] WebSocket 连接成功 [${new Date().toISOString()}]`);
      console.error(`   WebSocket URL: ${SD35_WS_URL}`);
      console.error(`   Prompt ID: ${promptId}`);
      console.error(`   连接耗时: ${elapsed} 秒`);
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    };
    
    ws.onmessage = (event) => {
      try {
        lastMessageTime = Date.now();
        messageCount++;
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        
        const data = JSON.parse(event.data);
        console.group(`📨 [SD3.5] WebSocket 消息 #${messageCount} (${elapsed}s)`);
        console.log('📨 消息类型:', data.type);
        console.log('🆔 Prompt ID:', data.prompt_id);
        console.log('🔢 节点:', data.node !== null && data.node !== undefined ? data.node : 'null (任务完成)');
        console.log('📦 完整数据:', data);
        console.log('⏱️ 已等待时间:', `${elapsed} 秒`);
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`📨 [SD3.5前端] WebSocket 消息 #${messageCount} [${new Date().toISOString()}]`);
        console.error(`   消息类型: ${data.type}`);
        console.error(`   Prompt ID: ${data.prompt_id}`);
        console.error(`   节点: ${data.node !== null && data.node !== undefined ? data.node : 'null (任务完成)'}`);
        console.error(`   已等待: ${elapsed} 秒`);
        if (data.type === 'progress' && data.value !== undefined && data.max !== undefined) {
          const progress = Math.round((data.value / data.max) * 100);
          console.error(`   进度: ${progress}% (${data.value}/${data.max})`);
        }
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        
        // 处理不同类型的消息
        if (data.type === 'executing') {
          if (data.node === null && data.prompt_id === promptId) {
            // 任务完成
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
            console.group('✅ [SD3.5] 任务执行完成');
            console.log('🆔 Prompt ID:', promptId);
            console.log('⏱️ 总耗时:', `${elapsed} 秒`);
            console.log('📊 收到消息总数:', messageCount);
            console.log('💡 下一步: 获取历史记录中的图片');
            console.groupEnd();
            
            // 同时输出到终端
            console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.error(`✅ [SD3.5前端] 任务执行完成 [${new Date().toISOString()}]`);
            console.error(`   Prompt ID: ${promptId}`);
            console.error(`   总耗时: ${elapsed} 秒`);
            console.error(`   收到消息数: ${messageCount}`);
            console.error('   下一步: 获取历史记录中的图片');
            console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            
            if (!isResolved) {
              isResolved = true;
              clearTimeout(timeoutTimer);
              clearInterval(heartbeatTimer);
              ws.close();
              
              // 需要等待一下再获取结果
              console.log('⏳ [SD3.5] 等待 1 秒后获取历史记录...');
              setTimeout(() => {
                console.log('📥 [SD3.5] 开始获取历史记录...');
                // 通过 history 接口获取结果
                fetchHistory(promptId)
                  .then((imageFilename) => {
                    const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(2);
                    console.log(`✅ [SD3.5] 成功获取图片文件名: ${imageFilename} (总耗时: ${totalElapsed}s)`);
                    if (onComplete) onComplete(imageFilename);
                    resolve(imageFilename);
                  })
                  .catch((error) => {
                    const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(2);
                    console.error(`❌ [SD3.5] 获取历史记录失败 (总耗时: ${totalElapsed}s):`, error);
                    if (onError) onError(error);
                    reject(error);
                  });
              }, 1000);
            }
          } else if (data.node !== null) {
            // 节点执行中
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
            console.log(`🔄 [SD3.5] 节点执行中: 节点 ${data.node} (${elapsed}s)`);
            if (onProgress) {
              onProgress({
                node: data.node,
                promptId: data.prompt_id,
              });
            }
          }
        } else if (data.type === 'progress') {
          // 进度更新
          const progress = data.max > 0 ? Math.round((data.value / data.max) * 100) : 0;
          const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
          console.log(`📊 [SD3.5] 生成进度: ${progress}% (${data.value}/${data.max}) (${elapsed}s)`);
          if (onProgress) {
            onProgress({
              value: data.value,
              max: data.max,
              promptId: data.prompt_id,
            });
          }
        } else if (data.type === 'execution_error') {
          // 执行错误
          const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
          const error = new Error(data.message || '执行错误');
          console.group('❌ [SD3.5] WebSocket 执行错误');
          console.error('🔴 错误类型: 服务器执行错误');
          console.error('🆔 Prompt ID:', promptId);
          console.error('📝 错误消息:', data.message);
          console.error('📦 错误数据:', data);
          console.error('⏱️ 失败前耗时:', `${elapsed} 秒`);
          console.error('📊 收到消息数:', messageCount);
          console.error('💡 可能原因:');
          console.error('   - Prompt JSON 格式错误');
          console.error('   - 节点配置错误');
          console.error('   - 服务器资源不足');
          console.error('   - 模型文件缺失或损坏');
          console.groupEnd();
          
          // 同时输出到终端
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          console.error(`❌ [SD3.5前端] 执行错误 [${new Date().toISOString()}]`);
          console.error(`   Prompt ID: ${promptId}`);
          console.error(`   错误消息: ${data.message || '未知错误'}`);
          console.error(`   失败前耗时: ${elapsed} 秒`);
          console.error(`   收到消息数: ${messageCount}`);
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          
          if (!isResolved) {
            isResolved = true;
            clearTimeout(timeoutTimer);
            clearInterval(heartbeatTimer);
            ws.close();
            if (onError) onError(error);
            reject(error);
          }
        } else if (data.type === 'executed') {
          // 节点执行完成，可能包含输出信息
          const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
          if (data.node && data.output && data.output.images) {
            const images = data.output.images;
            if (Array.isArray(images) && images.length > 0) {
              const imageInfo = images[0];
              const filename = imageInfo.filename || imageInfo.name || imageInfo;
              console.group('✅ [SD3.5] 从 executed 消息中获取到图片');
              console.log('🖼️ 图片文件名:', filename);
              console.log('🔢 节点 ID:', data.node);
              console.log('⏱️ 耗时:', `${elapsed} 秒`);
              console.groupEnd();
              
              // 同时输出到终端
              console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
              console.error(`✅ [SD3.5前端] 从 executed 消息获取图片 [${new Date().toISOString()}]`);
              console.error(`   图片文件名: ${filename}`);
              console.error(`   节点 ID: ${data.node}`);
              console.error(`   耗时: ${elapsed} 秒`);
              console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
              
              if (!isResolved) {
                isResolved = true;
                clearTimeout(timeoutTimer);
                clearInterval(heartbeatTimer);
                ws.close();
                if (onComplete) onComplete(filename);
                resolve(filename);
              }
            }
          } else {
            console.log(`ℹ️ [SD3.5] executed 消息（节点 ${data.node}），但未包含图片信息`);
          }
        } else {
          // 其他类型的消息
          console.log(`ℹ️ [SD3.5] 收到其他类型消息: ${data.type}`, data);
        }
      } catch (error) {
        console.error('❌ 解析 WebSocket 消息失败:', error);
      }
    };
    
    ws.onerror = (error) => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
      console.group('❌ [SD3.5] WebSocket 连接错误');
      console.error('🔴 错误类型: WebSocket 连接错误');
      console.error('📍 WebSocket URL:', SD35_WS_URL);
      console.error('🆔 Prompt ID:', promptId);
      console.error('📝 错误信息:', error);
      console.error('⏱️ 错误前耗时:', `${elapsed} 秒`);
      console.error('📊 收到消息数:', messageCount);
      console.error('💡 可能原因:');
      console.error('   - WebSocket 服务器未运行');
      console.error('   - WebSocket URL 错误');
      console.error('   - 网络连接问题');
      console.error('   - 代理配置问题');
      console.error('   - CORS 配置问题');
      console.groupEnd();
      
      // 同时输出到终端
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error(`❌ [SD3.5前端] WebSocket 连接错误 [${new Date().toISOString()}]`);
      console.error(`   WebSocket URL: ${SD35_WS_URL}`);
      console.error(`   Prompt ID: ${promptId}`);
      console.error(`   错误前耗时: ${elapsed} 秒`);
      console.error(`   收到消息数: ${messageCount}`);
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      
      if (!isResolved) {
        isResolved = true;
        clearTimeout(timeoutTimer);
        clearInterval(heartbeatTimer);
        const wsError = new Error(`[WebSocket错误] 无法连接到 ${SD35_WS_URL}`);
        if (onError) onError(wsError);
        reject(wsError);
      }
    };
    
    ws.onclose = (event) => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
      console.group('🔌 [SD3.5] WebSocket 连接已关闭');
      console.log('📍 WebSocket URL:', SD35_WS_URL);
      console.log('🆔 Prompt ID:', promptId);
      console.log('📊 关闭代码:', event.code);
      console.log('📝 关闭原因:', event.reason || '(无)');
      console.log('🧹 是否正常关闭:', event.wasClean);
      console.log('⏱️ 连接持续时间:', `${elapsed} 秒`);
      console.log('📊 收到消息总数:', messageCount);
      console.log('✅ 任务是否已完成:', isResolved);
      console.groupEnd();
      
      // 同时输出到终端
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error(`🔌 [SD3.5前端] WebSocket 连接已关闭 [${new Date().toISOString()}]`);
      console.error(`   WebSocket URL: ${SD35_WS_URL}`);
      console.error(`   Prompt ID: ${promptId}`);
      console.error(`   关闭代码: ${event.code}`);
      console.error(`   关闭原因: ${event.reason || '(无)'}`);
      console.error(`   是否正常关闭: ${event.wasClean}`);
      console.error(`   连接持续时间: ${elapsed} 秒`);
      console.error(`   收到消息数: ${messageCount}`);
      console.error(`   任务是否已完成: ${isResolved}`);
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      
      // 清理定时器
      if (timeoutTimer) clearTimeout(timeoutTimer);
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      
      // 如果连接意外关闭且任务未完成，尝试通过 history API 获取结果
      if (!isResolved && !event.wasClean) {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        console.group('⚠️ [SD3.5] WebSocket 连接意外关闭，尝试通过 History API 获取结果');
        console.warn('🔴 WebSocket 连接意外关闭');
        console.warn('🆔 Prompt ID:', promptId);
        console.warn('📊 关闭代码:', event.code);
        console.warn('⏱️ 已等待时间:', `${elapsed} 秒`);
        console.warn('📊 收到消息数:', messageCount);
        console.warn('💡 尝试通过 History API 获取结果...');
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`⚠️ [SD3.5前端] WebSocket 意外关闭，尝试获取结果 [${new Date().toISOString()}]`);
        console.error(`   Prompt ID: ${promptId}`);
        console.error(`   关闭代码: ${event.code}`);
        console.error(`   已等待: ${elapsed} 秒`);
        console.error(`   收到消息数: ${messageCount}`);
        console.error('   尝试通过 History API 获取结果...');
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        
        // 等待几秒后尝试获取历史记录（给服务器时间完成处理）
        const waitTime = elapsed > 60 ? 5000 : 3000; // 如果已经等待超过 60 秒，等待 5 秒，否则等待 3 秒
        console.log(`⏳ [SD3.5] 等待 ${waitTime / 1000} 秒后尝试获取历史记录...`);
        
        setTimeout(() => {
          if (!isResolved) {
            console.log('📥 [SD3.5] 开始通过 History API 获取结果...');
            fetchHistory(promptId)
              .then((imageFilename) => {
                if (!isResolved) {
                  isResolved = true;
                  const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(2);
                  console.group('✅ [SD3.5] 通过 History API 成功获取结果');
                  console.log('🖼️ 图片文件名:', imageFilename);
                  console.log('⏱️ 总耗时:', `${totalElapsed} 秒`);
                  console.log('💡 说明: WebSocket 连接断开，但任务已在服务器端完成');
                  console.groupEnd();
                  
                  // 同时输出到终端
                  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                  console.error(`✅ [SD3.5前端] 通过 History API 获取成功 [${new Date().toISOString()}]`);
                  console.error(`   图片文件名: ${imageFilename}`);
                  console.error(`   总耗时: ${totalElapsed} 秒`);
                  console.error('   说明: WebSocket 连接断开，但任务已在服务器端完成');
                  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                  
                  if (onComplete) onComplete(imageFilename);
                  resolve(imageFilename);
                }
              })
              .catch((historyError) => {
                if (!isResolved) {
                  isResolved = true;
                  const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(2);
                  const error = new Error(`[WebSocket错误] 连接意外关闭（代码: ${event.code}），且无法通过 History API 获取结果。已等待 ${totalElapsed} 秒。History API 错误: ${historyError.message}`);
                  
                  console.group('❌ [SD3.5] 无法通过 History API 获取结果');
                  console.error('🔴 错误类型: WebSocket 断开且 History API 失败');
                  console.error('🆔 Prompt ID:', promptId);
                  console.error('📊 WebSocket 关闭代码:', event.code);
                  console.error('⏱️ 总耗时:', `${totalElapsed} 秒`);
                  console.error('📊 收到消息数:', messageCount);
                  console.error('📝 History API 错误:', historyError.message);
                  console.error('💡 可能原因:');
                  console.error('   - 任务尚未完成');
                  console.error('   - 服务器处理失败');
                  console.error('   - 网络连接问题');
                  console.error('   - ComfyUI 服务器未运行');
                  console.groupEnd();
                  
                  // 同时输出到终端
                  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                  console.error(`❌ [SD3.5前端] 获取结果失败 [${new Date().toISOString()}]`);
                  console.error(`   Prompt ID: ${promptId}`);
                  console.error(`   WebSocket 关闭代码: ${event.code}`);
                  console.error(`   总耗时: ${totalElapsed} 秒`);
                  console.error(`   收到消息数: ${messageCount}`);
                  console.error(`   History API 错误: ${historyError.message}`);
                  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                  
                  if (onError) onError(error);
                  reject(error);
                }
              });
          }
        }, waitTime);
      }
    };
  });
};

/**
 * 获取历史记录中的图片文件名（带重试机制）
 * @param {string} promptId - prompt ID
 * @param {number} maxRetries - 最大重试次数，默认 3
 * @param {number} retryDelay - 重试延迟（毫秒），默认 2000
 * @returns {Promise<string>} 返回图片文件名
 */
const fetchHistory = async (promptId, maxRetries = 3, retryDelay = 2000) => {
  const historyUrl = `${SD35_API_URL}/history/${promptId}`;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    // 详细的请求日志
    console.group(`📤 [SD3.5] 获取历史记录请求 (尝试 ${attempt}/${maxRetries})`);
    console.log('📍 请求 URL:', historyUrl);
    console.log('🔧 请求方法: GET');
    console.log('🆔 Prompt ID:', promptId);
    console.log('🌐 API 基础地址:', SD35_API_URL);
    console.log('⏰ 请求时间:', new Date().toISOString());
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`📤 [SD3.5前端] 获取历史记录 (尝试 ${attempt}/${maxRetries}) [${new Date().toISOString()}]`);
    console.error(`   请求 URL: ${historyUrl}`);
    console.error(`   Prompt ID: ${promptId}`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    let response;
    let responseText = '';
    let responseHeaders = {};
    
    try {
    // 尝试获取历史记录
    // 配置 CORS：使用 mode: 'cors'，不发送 credentials 避免 403 错误
    response = await fetch(historyUrl, {
      method: 'GET',
      mode: 'cors', // 明确启用 CORS 模式
      credentials: 'omit', // 不发送 credentials，防止触发 403 错误
    });
    
    // 读取响应头
    responseHeaders = Object.fromEntries(response.headers.entries());
    responseText = await response.text();
    
    // 详细的响应日志
    console.group(`📥 [SD3.5] 历史记录响应 (${response.status} ${response.statusText})`);
    console.log('📍 响应 URL:', response.url);
    console.log('📊 状态码:', response.status);
    console.log('📝 状态文本:', response.statusText);
    console.log('📋 响应头:', responseHeaders);
    console.log('📄 响应体长度:', `${(responseText.length / 1024).toFixed(2)} KB`);
    console.log('📄 响应体预览:', responseText.substring(0, 500) + (responseText.length > 500 ? '...' : ''));
    console.groupEnd();
    
    // 同时输出到终端
    logToTerminal.response(
      response.url,
      response.status,
      response.statusText,
      !response.ok,
      responseText
    );
    
    if (!response.ok) {
      // 服务器返回错误
      console.group('❌ [SD3.5] 服务器返回错误');
      console.error('🔴 错误类型: 服务器端错误');
      console.error('📍 错误 URL:', response.url);
      console.error('📊 HTTP 状态码:', response.status);
      console.error('📝 HTTP 状态文本:', response.statusText);
      console.error('📋 响应头:', responseHeaders);
      console.error('📄 错误响应体:', responseText);
      console.error('💡 可能原因:');
      const suggestions = [];
      if (response.status === 404) {
        console.error('   - 历史记录不存在（Prompt ID 错误或任务未完成）');
        suggestions.push('历史记录不存在（Prompt ID 错误或任务未完成）');
      } else if (response.status >= 500) {
        console.error('   - 服务器内部错误');
        suggestions.push('服务器内部错误');
      }
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.error(
        '服务器错误',
        response.url,
        `${response.status} ${response.statusText}: ${responseText.substring(0, 200)}`,
        suggestions
      );
      
      throw new Error(`[服务器错误 ${response.status}] ${response.statusText}: ${responseText}`);
    }
    
    // 解析 JSON 响应
    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      console.error('❌ [SD3.5] JSON 解析失败:', parseError);
      console.error('📄 原始响应:', responseText);
      throw new Error(`响应不是有效的 JSON: ${responseText.substring(0, 200)}`);
    }
    
    console.group('📜 [SD3.5] 历史记录数据');
    console.log('📦 历史记录:', data);
    console.groupEnd();
    
    // ComfyUI 历史记录格式：{ [promptId]: { outputs: { [nodeId]: { images: [...] } } } }
    if (data && typeof data === 'object') {
      // 查找包含 promptId 的键
      const historyEntry = data[promptId] || Object.values(data).find(entry => entry && entry.outputs);
      
      if (historyEntry && historyEntry.outputs) {
        const outputs = historyEntry.outputs;
        // 查找 SaveImage 节点的输出（节点 ID 是 8，但为了兼容性也查找所有节点）
        // ⚠️ 重要：优先查找节点 8（SaveImage），如果找不到再查找其他节点
        console.group('🔍 [SD3.5] 查找 SaveImage 节点输出');
        console.log('📋 所有输出节点 ID:', Object.keys(outputs));
        console.log('🔢 期望的 SaveImage 节点 ID: 8');
        console.log('📦 所有输出节点:', outputs);
        console.groupEnd();
        
        // 优先查找节点 8
        if (outputs["8"] && outputs["8"].images && Array.isArray(outputs["8"].images) && outputs["8"].images.length > 0) {
          const imageInfo = outputs["8"].images[0];
          const filename = imageInfo.filename || imageInfo.name || imageInfo;
          console.group('✅ [SD3.5] 在节点 8 (SaveImage) 找到生成的图片');
          console.log('🖼️ 图片文件名:', filename);
          console.log('🔢 节点 ID: 8 (SaveImage)');
          console.log('📦 图片信息:', imageInfo);
          console.groupEnd();
          
          // 同时输出到终端
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          console.error(`✅ [SD3.5前端] 在节点 8 找到图片 [${new Date().toISOString()}]`);
          console.error(`   图片文件名: ${filename}`);
          console.error(`   节点 ID: 8 (SaveImage)`);
          console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          
          return filename;
        }
        
        // 如果节点 8 没有，查找其他节点（兼容性）
        for (const nodeId in outputs) {
          if (outputs[nodeId].images && Array.isArray(outputs[nodeId].images) && outputs[nodeId].images.length > 0) {
            const imageInfo = outputs[nodeId].images[0];
            const filename = imageInfo.filename || imageInfo.name || imageInfo;
            console.group(`✅ [SD3.5] 在节点 ${nodeId} 找到生成的图片（非预期的节点）`);
            console.log('🖼️ 图片文件名:', filename);
            console.log('🔢 节点 ID:', nodeId);
            console.log('⚠️ 注意: 这不是预期的节点 8 (SaveImage)');
            console.log('📦 图片信息:', imageInfo);
            console.groupEnd();
            
            // 同时输出到终端
            console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.error(`✅ [SD3.5前端] 在节点 ${nodeId} 找到图片 [${new Date().toISOString()}]`);
            console.error(`   图片文件名: ${filename}`);
            console.error(`   节点 ID: ${nodeId} (⚠️ 不是预期的节点 8)`);
            console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            
            return filename;
          }
        }
      }
    }
    
    // 如果历史记录格式不同，尝试从整个响应中查找
    if (data && typeof data === 'object') {
      // 递归查找所有包含 images 的对象
      const findImages = (obj, path = '') => {
        if (Array.isArray(obj)) {
          for (let i = 0; i < obj.length; i++) {
            const result = findImages(obj[i], `${path}[${i}]`);
            if (result) return result;
          }
        } else if (obj && typeof obj === 'object') {
          if (obj.images && Array.isArray(obj.images) && obj.images.length > 0) {
            const imageInfo = obj.images[0];
            return imageInfo.filename || imageInfo.name || imageInfo;
          }
          for (const key in obj) {
            const result = findImages(obj[key], path ? `${path}.${key}` : key);
            if (result) return result;
          }
        }
        return null;
      };
      
      const filename = findImages(data);
      if (filename) {
        console.group('✅ [SD3.5] 递归查找到图片');
        console.log('🖼️ 图片文件名:', filename);
        console.groupEnd();
        return filename;
      }
    }
    
      // 未找到图片
      console.group('❌ [SD3.5] 未找到生成的图片');
      console.error('🔴 错误类型: 数据解析错误');
      console.error('🆔 Prompt ID:', promptId);
      console.error('📦 历史记录数据:', data);
      console.error('💡 可能原因:');
      console.error('   - 任务尚未完成');
      console.error('   - 历史记录格式不符合预期');
      console.error('   - SaveImage 节点未执行');
      console.groupEnd();
      
      // 如果是最后一次尝试，直接抛出错误
      if (attempt === maxRetries) {
        throw new Error('未找到生成的图片');
      }
      
      // 否则等待后重试
      console.log(`⏳ [SD3.5] 等待 ${retryDelay / 1000} 秒后重试...`);
      await new Promise(resolve => setTimeout(resolve, retryDelay));
      continue; // 继续下一次循环
      
    } catch (error) {
    // 网络错误或其他客户端错误
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      console.group('❌ [SD3.5] 网络请求失败');
      console.error('🔴 错误类型: 客户端网络错误');
      console.error('📍 请求 URL:', historyUrl);
      console.error('📝 错误信息:', error.message);
      console.error('💡 可能原因:');
      console.error('   - 无法连接到服务器');
      console.error('   - 服务器未运行或地址错误');
      console.error('   - 网络连接问题');
      console.groupEnd();
      
      // 同时输出到终端
      logToTerminal.error(
        '网络错误',
        historyUrl,
        error.message,
        [
          '无法连接到服务器',
          '服务器未运行或地址错误',
          '网络连接问题'
        ]
      );
      
      throw new Error(`[网络错误] 无法连接到 SD3.5 服务器 ${SD35_API_URL}: ${error.message}`);
    }
    
      // 如果是我们抛出的错误，检查是否需要重试
      const isRetryable = error.message.includes('[服务器错误 404]') || 
                          error.message.includes('[网络错误]') ||
                          error.message.includes('未找到生成的图片');
      
      if (isRetryable && attempt < maxRetries) {
        console.group(`⚠️ [SD3.5] 尝试 ${attempt} 失败，准备重试`);
        console.warn('📝 错误信息:', error.message);
        console.warn(`⏳ 等待 ${retryDelay / 1000} 秒后重试 (${attempt + 1}/${maxRetries})...`);
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`⚠️ [SD3.5前端] 尝试 ${attempt} 失败，准备重试 [${new Date().toISOString()}]`);
        console.error(`   错误信息: ${error.message}`);
        console.error(`   等待 ${retryDelay / 1000} 秒后重试 (${attempt + 1}/${maxRetries})`);
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        continue; // 继续下一次循环
      }
      
      // 如果是最后一次尝试或不可重试的错误，直接抛出
      if (attempt === maxRetries || !isRetryable) {
        // 其他未知错误
        console.group('❌ [SD3.5] 获取历史记录失败');
        console.error('🔴 错误类型: 未知错误');
        console.error('📍 请求 URL:', historyUrl);
        console.error('📝 错误信息:', error);
        console.error('📚 错误堆栈:', error.stack);
        console.error(`📊 尝试次数: ${attempt}/${maxRetries}`);
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`❌ [SD3.5前端] 获取历史记录失败 [${new Date().toISOString()}]`);
        console.error(`   请求 URL: ${historyUrl}`);
        console.error(`   错误信息: ${error.message || String(error)}`);
        console.error(`   尝试次数: ${attempt}/${maxRetries}`);
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        
        throw error;
      }
    }
  }
  
  // 如果所有重试都失败（理论上不应该到达这里）
  throw new Error(`获取历史记录失败：已重试 ${maxRetries} 次`);
};

/**
 * 获取图片 URL
 * @param {string} filename - 图片文件名
 * @returns {string} 图片 URL
 */
export const getImageUrl = (filename) => {
  return `${SD35_API_URL}/view?filename=${filename}`;
};

/**
 * SD3.5 图片生成主函数
 * @param {string} prompt - 提示词
 * @param {File|Array<File>} referenceImages - 参考图片（可选）
 * @param {string} aspectRatio - 宽高比（可选，如 "1:1", "16:9" 等）
 * @param {Object} options - 其他选项
 * @returns {Promise<Object>} 返回生成结果 { image_url, image_data }
 */
/**
 * 检测提示词是否为中文
 * @param {string} prompt - 提示词
 * @returns {boolean} 是否为中文
 */
const isChinesePrompt = (prompt) => {
  if (!prompt || typeof prompt !== 'string') {
    return false;
  }
  // 检测中文字符（包括中文标点）
  const chineseRegex = /[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/;
  const chineseCharCount = (prompt.match(/[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/g) || []).length;
  const totalCharCount = prompt.length;
  // 如果中文字符占比超过 20%，认为是中文提示词
  return chineseRegex.test(prompt) && (chineseCharCount / totalCharCount) > 0.2;
};

/**
 * 将中文提示词翻译成英文（专门为 SD3.5 使用）
 * ⚠️ 重要：此功能仅用于 SD3.5 模式，不影响 banana 等其他模式
 * 复用 optimize-prompt 接口，通过特殊的翻译指令实现翻译功能
 * @param {string} chinesePrompt - 中文提示词
 * @returns {Promise<string>} 英文提示词
 */
const translatePromptToEnglish = async (chinesePrompt) => {
  try {
    console.group('🌐 [SD3.5] 翻译中文提示词为英文');
    console.log('📝 原始中文提示词:', chinesePrompt);
    console.log('💡 提示: SD3.5 对中文理解能力较差，需要翻译成英文');
    console.log('🔧 方法: 复用 optimize-prompt 接口，使用翻译指令');
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`🌐 [SD3.5前端] 开始翻译中文提示词 [${new Date().toISOString()}]`);
    console.error(`   原始提示词: ${chinesePrompt.substring(0, 100)}${chinesePrompt.length > 100 ? '...' : ''}`);
    console.error(`   方法: 复用 optimize-prompt 接口（翻译模式）`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    // ⚠️ 复用 optimize-prompt 接口，但使用特殊的翻译指令
    // 通过构造一个翻译指令，让 Gemini 模型执行翻译功能
    // ⚠️ 重要：要求精准直译，不要扩展或添加细节，保持原意完全不变
    // ⚠️ 重要：翻译指令要求精准直译，不扩展或添加细节
    // 这确保生图与原图差异最小，精准还原用户意图
    const translationRequest = `请将以下中文图片生成提示词准确直译成英文。

⚠️ 严格按要求执行（这非常重要，影响生图精准度）：
1. 只做直译，不做任何优化、扩展、润色或添加细节
2. 保持原意完全不变，绝对不要添加任何视觉细节描述（如光线、色彩、构图、风格、材质等）
3. 不要添加任何形容词、修饰语或额外描述
4. 不要润色或美化文字，只做最基本的词对词翻译
5. 直接输出英文翻译结果，不要添加任何说明文字、前缀、后缀或标点符号
6. 如果提示词中包含专有名词、品牌名等，保持英文原样或使用标准英文翻译
7. 翻译结果应尽可能简短、准确，不要扩展原意

中文提示词：${chinesePrompt}

英文翻译（仅直译，不扩展，不添加细节）：`;
    
    // 获取 API 基础地址（与 chatAPI 使用相同的地址）
    // ⚠️ 注意：需要使用后端 API 地址，不是 SD3.5 服务器地址
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    
    // 调用 optimize-prompt 接口（复用后端优化接口）
    // ⚠️ 重要：后端会自动检测翻译指令，如果是翻译请求则执行翻译，否则执行优化
    // 这样既支持 SD3.5 的翻译需求，又不影响 banana 的优化逻辑
    const response = await fetch(`${API_BASE_URL}/api/optimize-prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: translationRequest,  // 传入翻译指令（不是原始提示词）
      }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`翻译请求失败: ${response.status} ${response.statusText} - ${errorText.substring(0, 200)}`);
    }
    
    const data = await response.json();
    
    // 提取翻译结果
    let translatedPrompt = data.optimized_prompt || data.original_prompt || chinesePrompt;
    
    // ⚠️ 重要：清理可能的多余内容
    // optimize_prompt 可能返回包含说明文字的内容，需要提取纯翻译结果
    if (translatedPrompt.includes('英文翻译：') || translatedPrompt.includes('English:')) {
      // 尝试提取翻译后的内容（在"英文翻译："之后的部分）
      const lines = translatedPrompt.split('\n');
      for (const line of lines) {
        const cleanLine = line.trim();
        // 找到第一个不包含翻译相关关键词的长文本行
        if (cleanLine && 
            cleanLine.length > 5 && 
            !cleanLine.toLowerCase().includes('translation') &&
            !cleanLine.includes('翻译') && 
            !cleanLine.includes('Translation') &&
            !cleanLine.includes('英文') &&
            !cleanLine.includes('English') &&
            !cleanLine.includes('中文') &&
            !cleanLine.includes('Chinese') &&
            !cleanLine.includes('提示词') &&
            !cleanLine.includes('Prompt')) {
          translatedPrompt = cleanLine;
          break;
        }
      }
    }
    
    // 如果翻译结果仍然包含原始的中文提示词，说明提取失败，尝试其他方法
    if (translatedPrompt.includes(chinesePrompt)) {
      // 尝试从包含原始提示词的文本中提取翻译部分
      const parts = translatedPrompt.split(chinesePrompt);
      if (parts.length > 1 && parts[parts.length - 1].trim().length > 5) {
        translatedPrompt = parts[parts.length - 1].trim();
        // 再次清理说明文字
        translatedPrompt = translatedPrompt.replace(/^(英文翻译|English Translation|Translation):?\s*/i, '');
      }
    }
    
    // 验证翻译结果（应该不包含或仅包含少量中文字符）
    const chineseCharCount = (translatedPrompt.match(/[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/g) || []).length;
    const totalCharCount = translatedPrompt.length;
    const chineseRatio = totalCharCount > 0 ? chineseCharCount / totalCharCount : 0;
    
    if (chineseRatio > 0.1) {
      console.warn('⚠️ [SD3.5] 翻译结果仍包含较多中文字符，可能需要重新翻译');
      console.warn('📝 翻译结果:', translatedPrompt);
      console.warn('💡 提示: 翻译可能不完整，建议检查后端 optimize_prompt 函数的响应');
    }
    
    console.group('✅ [SD3.5] 提示词翻译完成');
    console.log('📝 原始中文:', chinesePrompt);
    console.log('🌐 翻译英文:', translatedPrompt);
    console.log('📊 中文字符占比:', `${(chineseRatio * 100).toFixed(1)}%`);
    console.log('✅ 翻译质量:', chineseRatio < 0.1 ? '良好' : '可能不完整');
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`✅ [SD3.5前端] 提示词翻译完成 [${new Date().toISOString()}]`);
    console.error(`   原始中文: ${chinesePrompt.substring(0, 80)}${chinesePrompt.length > 80 ? '...' : ''}`);
    console.error(`   翻译英文: ${translatedPrompt.substring(0, 80)}${translatedPrompt.length > 80 ? '...' : ''}`);
    console.error(`   中文字符占比: ${(chineseRatio * 100).toFixed(1)}%`);
    console.error(`   翻译质量: ${chineseRatio < 0.1 ? '良好' : '可能不完整'}`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    return translatedPrompt;
  } catch (error) {
    console.error('❌ [SD3.5] 提示词翻译失败:', error);
    console.warn('⚠️ [SD3.5] 翻译失败，使用原始中文提示词（可能导致 SD3.5 理解偏差）');
    console.error('错误详情:', {
      message: error.message,
      name: error.name,
      stack: error.stack
    });
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`❌ [SD3.5前端] 提示词翻译失败 [${new Date().toISOString()}]`);
    console.error(`   错误信息: ${error.message}`);
    console.error(`   将使用原始中文提示词（可能导致 SD3.5 理解偏差）`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    // 翻译失败时，返回原始提示词（避免阻断流程）
    return chinesePrompt;
  }
};

export const generateImage = async (prompt, referenceImages = null, aspectRatio = null, options = {}) => {
  const startTime = Date.now();
  
  // ⚠️ 重要：检测中文提示词，如果检测到中文，先翻译成英文
  // 这个功能仅用于 SD3.5 模式，不影响 banana 等其他模式
  let finalPrompt = prompt;
  const originalPrompt = prompt;
  
  if (isChinesePrompt(prompt)) {
    console.group('🔍 [SD3.5] 检测到中文提示词');
    console.log('📝 原始提示词:', prompt);
    console.log('💡 提示: SD3.5 对中文理解能力较差，需要翻译成英文');
    console.log('🌐 开始翻译为英文...');
    console.groupEnd();
    
    try {
      finalPrompt = await translatePromptToEnglish(prompt);
      
      if (finalPrompt === prompt) {
        console.warn('⚠️ [SD3.5] 翻译失败或返回原文本，使用原始提示词');
      } else {
        console.log('✅ [SD3.5] 翻译成功，将使用英文提示词:', finalPrompt.substring(0, 100));
      }
    } catch (error) {
      console.error('❌ [SD3.5] 翻译过程出错:', error);
      console.warn('⚠️ [SD3.5] 翻译失败，使用原始提示词（可能导致 SD3.5 理解偏差）');
      finalPrompt = prompt; // 翻译失败时使用原始提示词
    }
  } else {
    console.log('ℹ️ [SD3.5] 提示词为英文或非中文，无需翻译');
  }
  
  console.group('🎨 [SD3.5] 开始图片生成');
  console.log('📝 原始提示词:', originalPrompt);
  if (finalPrompt !== originalPrompt) {
    console.log('🌐 翻译后提示词:', finalPrompt);
  }
  console.log('📐 宽高比:', aspectRatio || '默认 (1:1)');
  console.log('🖼️ 参考图片:', referenceImages ? 
    (Array.isArray(referenceImages) ? `${referenceImages.length} 张` : '1 张') : 
    '无');
  console.log('⚙️ 选项:', {
    steps: options.steps || 4,
    cfg: options.cfg || 1.0,
    seed: options.seed || '(随机)',
    negativePrompt: options.negativePrompt || 'low quality'
  });
  console.log('🌐 API 地址:', SD35_API_URL);
  console.log('⏰ 开始时间:', new Date().toISOString());
  console.groupEnd();
  
  // 同时输出到终端
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.error(`🎨 [SD3.5前端] 开始图片生成 [${new Date().toISOString()}]`);
  console.error(`   提示词: ${prompt.substring(0, 50)}${prompt.length > 50 ? '...' : ''}`);
  console.error(`   宽高比: ${aspectRatio || '默认 (1:1)'}`);
  console.error(`   参考图片: ${referenceImages ? (Array.isArray(referenceImages) ? `${referenceImages.length} 张` : '1 张') : '无'}`);
  console.error(`   API 地址: ${SD35_API_URL}`);
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  try {
    
    // 解析宽高比
    let width = 1024;
    let height = 1024;
    if (aspectRatio) {
      const [w, h] = aspectRatio.split(':').map(Number);
      if (w && h) {
        // 保持总像素数大致相同，调整宽高
        const ratio = w / h;
        if (ratio > 1) {
          width = 1024;
          height = Math.round(1024 / ratio);
        } else {
          width = Math.round(1024 * ratio);
          height = 1024;
        }
      }
    }
    
    // ⚠️ 重要：上传参考图片（图生图模式）
    // 在提交 Prompt 之前，先调用 /upload/image 接口将图片上传到 ComfyUI 服务器
    // ⚠️ 支持多张图片上传（双人合影模式）
    let uploadedImageName = null;
    let uploadedImageNames = null;  // ⚠️ 多图模式：存储所有上传后的文件名
    if (referenceImages) {
      const images = Array.isArray(referenceImages) ? referenceImages : [referenceImages];
      
      if (images.length > 0 && images[0]) {
        console.group('📤 [SD3.5] 上传参考图片（图生图模式）');
        console.log('📸 图片总数:', images.length);
        console.log('📁 第一张图片文件名:', images[0].name);
        console.log('📦 第一张图片大小:', `${(images[0].size / 1024).toFixed(2)} KB`);
        console.log('📄 第一张图片类型:', images[0].type);
        
        // ⚠️ 多图模式：上传所有图片
        if (images.length >= 2) {
          console.log('👥 [SD3.5] 检测到多张参考图片，启用双人合影模式');
          console.log('📁 所有图片:', images.map(img => img.name).join(', '));
          console.log('💡 提示: 将使用 IP-Adapter + ConditioningSetMask 实现分区域引导');
        }
        console.log('🌐 上传接口: /upload/image');
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`📤 [SD3.5前端] 开始上传参考图片 [${new Date().toISOString()}]`);
        console.error(`   图片总数: ${images.length}`);
        console.error(`   第一张图片: ${images[0].name} (${(images[0].size / 1024).toFixed(2)} KB)`);
        if (images.length >= 2) {
          console.error(`   👥 启用双人合影模式：上传所有图片`);
          images.slice(1).forEach((img, idx) => {
            console.error(`   图片 ${idx + 2}: ${img.name} (${(img.size / 1024).toFixed(2)} KB)`);
          });
        }
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        
        // 上传所有图片（多图模式）
        const uploadedNames = [];
        for (let i = 0; i < images.length; i++) {
          const img = images[i];
          const uploadedName = await uploadImage(img);
          uploadedNames.push(uploadedName);
          
          console.group(`✅ [SD3.5] 图片 ${i + 1} 上传成功`);
          console.log('📁 上传后的文件名:', uploadedName);
          console.log('📁 文件名类型:', typeof uploadedName);
          console.log('📁 文件名值:', JSON.stringify(uploadedName));
          console.groupEnd();
          
          // 验证文件名
          if (!uploadedName || uploadedName === 'undefined' || uploadedName === undefined) {
            throw new Error(`上传图片 ${i + 1} (${img.name}) 后未获取到有效的文件名`);
          }
        }
        
        // 设置上传后的文件名（单图和多图模式）
        uploadedImageName = uploadedNames[0];  // 保持向后兼容
        uploadedImageNames = uploadedNames.length > 1 ? uploadedNames : null;  // 多图模式
        
        console.group('✅ [SD3.5] 所有参考图片上传完成');
        console.log('📁 上传后的文件名（单图模式）:', uploadedImageName);
        console.log('📁 上传后的文件名（多图模式）:', uploadedImageNames);
        console.log('📸 图片数量:', uploadedNames.length);
        console.log('💡 下一步: 将文件名填充到 LoadImage 节点的 image 字段');
        if (uploadedNames.length === 2) {
          console.log('👥 双人合影模式: 左区域使用图片1，右区域使用图片2');
        }
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`✅ [SD3.5前端] 所有参考图片上传完成 [${new Date().toISOString()}]`);
        console.error(`   图片数量: ${uploadedNames.length}`);
        console.error(`   上传后的文件名: ${JSON.stringify(uploadedNames)}`);
        if (uploadedNames.length === 2) {
          console.error(`   👥 双人合影模式: 左区域使用图片1，右区域使用图片2`);
        }
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      } else {
        console.log('ℹ️ [SD3.5] 无参考图片，使用文生图模式');
      }
    } else {
      console.log('ℹ️ [SD3.5] 无参考图片，使用文生图模式');
    }
    
    // 构建 prompt JSON
    console.group('🔨 [SD3.5] 构建 Prompt JSON');
    console.log('📝 提示词:', prompt);
    console.log('📐 尺寸:', `${width}x${height}`);
    console.log('🖼️ 参考图片文件名:', uploadedImageName || '无');
    console.log('⚙️ 参数:', {
      steps: options.steps || 4,
      cfg: options.cfg || 1.0,
      seed: options.seed || '(随机)',
      denoise: uploadedImageName ? (options.denoise || 0.7) : 1.0
    });
    console.groupEnd();
    
    // ⚠️ 重要：图生图模式下，denoise（重绘幅度）应设为可选参数，默认 0.75
    // denoise 范围：0.0-1.0
    // - 0.0: 完全保留原图（几乎不变化）
    // - 1.0: 完全重新生成（等同于文生图）
    // - 0.75: 推荐值，平衡原图保留和生成变化
    const defaultDenoise = uploadedImageName ? 0.75 : 1.0; // 图生图默认 0.75，文生图默认 1.0
    const finalDenoise = options.denoise !== undefined ? options.denoise : defaultDenoise;
    
    console.group('⚙️ [SD3.5] 生成参数配置');
    console.log('🖼️ 模式:', uploadedImageName ? '图生图 (Img2Img)' : '文生图 (Text2Img)');
    console.log('📝 提示词:', prompt);
    console.log('📐 尺寸:', `${width}x${height}`);
    console.log('🖼️ 参考图片:', uploadedImageName || '无');
    console.log('🎨 Denoise (重绘幅度):', finalDenoise, uploadedImageName ? '(图生图模式)' : '(文生图模式)');
    console.log('⚙️ 其他参数:', {
      steps: options.steps || 4,
      cfg: options.cfg || 1.0,
      seed: options.seed || '(随机)',
      negativePrompt: options.negativePrompt || 'low quality'
    });
    console.groupEnd();
    
    // ⚠️ 重要：使用翻译后的英文提示词构建 Prompt JSON（商业级 FaceID 工作流）
    // ⚠️ 多图模式：上传后的文件名数组（双人合影模式）
    const promptJSON = buildPromptJSON({
      prompt: finalPrompt,  // 使用翻译后的英文提示词（如果是中文）
      negativePrompt: options.negativePrompt || 'low quality',
      width,
      height,
      uploadedImageName,  // 单图模式：第一张图片的文件名（向后兼容）
      uploadedImageNames, // ⚠️ 多图模式：所有上传后的文件名数组（双人合影模式）
      seed: options.seed,
      steps: options.steps || 4,
      cfg: options.cfg || 1.0,
      denoise: finalDenoise, // 使用计算后的 denoise 值
      enableFaceID: options.enableFaceID !== false, // 默认启用 FaceID
      enableControlNet: options.enableControlNet !== false, // 默认启用 ControlNet
      enableFaceDetailer: options.enableFaceDetailer !== false, // 默认启用面部修复
    });
    
    // 验证 prompt JSON 中的 LoadImage 节点
    if (uploadedImageName && promptJSON["9"]) {
      console.group('🔍 [SD3.5] 验证 LoadImage 节点');
      console.log('🔢 节点 ID: 9');
      console.log('📦 节点类型:', promptJSON["9"].class_type);
      console.log('📁 节点中的文件名:', promptJSON["9"].inputs.image);
      console.log('📁 上传返回的文件名:', uploadedImageName);
      console.log('✅ 文件名匹配:', promptJSON["9"].inputs.image === uploadedImageName ? '是' : '否');
      if (promptJSON["9"].inputs.image !== uploadedImageName) {
        console.error('❌ 警告：LoadImage 节点中的文件名与上传返回的文件名不匹配！');
      }
      console.groupEnd();
    }
    
    // 提交 prompt
    console.group('📤 [SD3.5] 提交 Prompt');
    console.log('📋 Prompt JSON 节点数量:', Object.keys(promptJSON).length);
    console.log('🔢 SaveImage 节点 ID: 8');
    console.log('📦 SaveImage 节点类型:', promptJSON["8"]?.class_type);
    console.groupEnd();
    
    // 判断是文生图还是合影模式
    const isGroupPhoto = uploadedImageNames && uploadedImageNames.length >= 2;
    const promptId = isGroupPhoto 
      ? await submitPromptForGroupPhoto(promptJSON)
      : await submitPromptForTextToImage(promptJSON);
    
    // ⚠️ 重要：立即启动监听，确保不会错过任何进度更新
    console.group('⏳ [SD3.5] 准备启动进度监听');
    console.log('🆔 Prompt ID:', promptId);
    console.log('⏰ 启动时间:', new Date().toISOString());
    console.log('💡 提示: watchProgress 将在 submitPrompt 成功后立即启动');
    console.groupEnd();
    
    // 监听进度
    let progressValue = 0;
    const watchStartTime = Date.now();
    console.group('⏳ [SD3.5] 监听生成进度');
    console.log('🆔 Prompt ID:', promptId);
    console.log('⏰ 开始监听时间:', new Date().toISOString());
    console.log('⏱️ 超时设置: 5 分钟');
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`⏳ [SD3.5前端] 开始监听进度 [${new Date().toISOString()}]`);
    console.error(`   Prompt ID: ${promptId}`);
    console.error(`   超时设置: 5 分钟`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    const imageFilename = await watchProgress(
      promptId,
      (progress) => {
        // 更新进度
        const elapsed = ((Date.now() - watchStartTime) / 1000).toFixed(2);
        if (progress.value !== undefined && progress.max !== undefined) {
          progressValue = Math.round((progress.value / progress.max) * 100);
          console.log(`📊 [SD3.5] 生成进度: ${progressValue}% (${elapsed}s)`);
        } else if (progress.node !== undefined) {
          console.log(`🔄 [SD3.5] 节点执行中: 节点 ${progress.node} (${elapsed}s)`);
        }
      },
      (filename) => {
        const elapsed = ((Date.now() - watchStartTime) / 1000).toFixed(2);
        console.group('✅ [SD3.5] 图片生成完成');
        console.log('🖼️ 图片文件名:', filename);
        console.log('⏱️ 监听耗时:', `${elapsed} 秒`);
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`✅ [SD3.5前端] 图片生成完成 [${new Date().toISOString()}]`);
        console.error(`   图片文件名: ${filename}`);
        console.error(`   监听耗时: ${elapsed} 秒`);
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      },
      (error) => {
        const elapsed = ((Date.now() - watchStartTime) / 1000).toFixed(2);
        console.group('❌ [SD3.5] 生成失败');
        console.error('📝 错误信息:', error);
        console.error('⏱️ 失败前耗时:', `${elapsed} 秒`);
        console.error('📚 错误堆栈:', error.stack);
        console.groupEnd();
        
        // 同时输出到终端
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`❌ [SD3.5前端] 生成失败 [${new Date().toISOString()}]`);
        console.error(`   错误信息: ${error.message}`);
        console.error(`   失败前耗时: ${elapsed} 秒`);
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      },
      5 * 60 * 1000 // 5 分钟超时
    );
    
    // 获取图片 URL
    const imageUrl = getImageUrl(imageFilename);
    console.group('📥 [SD3.5] 下载生成的图片');
    console.log('🖼️ 图片 URL:', imageUrl);
    console.log('📁 文件名:', imageFilename);
    console.groupEnd();
    
    // 将图片转换为 base64（用于统一返回格式）
    let imageResponse;
    try {
      // 配置 CORS：使用 mode: 'cors'，不发送 credentials 避免 403 错误
      imageResponse = await fetch(imageUrl, {
        method: 'GET',
        mode: 'cors', // 明确启用 CORS 模式
        credentials: 'omit', // 不发送 credentials，防止触发 403 错误
      });
      if (!imageResponse.ok) {
        throw new Error(`下载图片失败: ${imageResponse.status} ${imageResponse.statusText}`);
      }
    } catch (fetchError) {
      console.group('❌ [SD3.5] 下载图片失败');
      console.error('🔴 错误类型: 图片下载错误');
      console.error('📍 图片 URL:', imageUrl);
      console.error('📝 错误信息:', fetchError);
      console.groupEnd();
      throw new Error(`[下载错误] 无法下载生成的图片: ${fetchError.message}`);
    }
    
    // 先读取完整的响应数据
    const imageArrayBuffer = await imageResponse.arrayBuffer();
    console.group('🔍 [SD3.5] 验证图片响应');
    console.log('📦 ArrayBuffer 大小:', `${(imageArrayBuffer.byteLength / 1024).toFixed(2)} KB`);
    console.log('📦 Content-Type:', imageResponse.headers.get('content-type'));
    console.log('📦 Content-Length:', imageResponse.headers.get('content-length'));
    console.log('📦 实际数据大小:', imageArrayBuffer.byteLength, 'bytes');
    console.groupEnd();
    
    // 验证数据大小（PNG 图片通常至少几 KB）
    if (imageArrayBuffer.byteLength < 1000) {
      console.error('❌ [SD3.5] 警告：图片数据过小，可能不完整！');
      console.error('📦 数据大小:', imageArrayBuffer.byteLength, 'bytes');
      throw new Error(`图片数据过小（${imageArrayBuffer.byteLength} bytes），可能下载不完整`);
    }
    
    // 从 ArrayBuffer 创建 Blob
    const contentType = imageResponse.headers.get('content-type') || 'image/png';
    const imageBlob = new Blob([imageArrayBuffer], { type: contentType });
    
    // 验证 blob 类型
    console.group('🔍 [SD3.5] 验证图片 Blob');
    console.log('📦 Blob 类型:', imageBlob.type);
    console.log('📦 Blob 大小:', `${(imageBlob.size / 1024).toFixed(2)} KB`);
    console.log('📦 Blob 是否有效:', imageBlob.size > 0);
    console.log('📦 Blob 大小与 ArrayBuffer 是否一致:', imageBlob.size === imageArrayBuffer.byteLength);
    console.groupEnd();
    
    // 如果 blob 类型为空或不正确，尝试从 Content-Type 获取
    let blobType = imageBlob.type;
    if (!blobType || blobType === 'application/octet-stream') {
      const contentType = imageResponse.headers.get('content-type');
      if (contentType && contentType.startsWith('image/')) {
        blobType = contentType;
        console.log(`⚠️ [SD3.5] Blob 类型为空，使用 Content-Type: ${blobType}`);
      } else {
        // 默认使用 PNG（ComfyUI 通常返回 PNG）
        blobType = 'image/png';
        console.log(`⚠️ [SD3.5] 无法确定图片类型，使用默认类型: ${blobType}`);
      }
    }
    
    const reader = new FileReader();
    const imageData = await new Promise((resolve, reject) => {
      let loadStartTime = Date.now();
      
      reader.onloadstart = () => {
        console.log('📖 [SD3.5] FileReader 开始读取 Blob...');
        console.log('📦 Blob 大小:', `${(imageBlob.size / 1024).toFixed(2)} KB`);
      };
      
      reader.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          console.log(`📖 [SD3.5] FileReader 读取进度: ${percent}% (${(event.loaded / 1024).toFixed(2)} KB / ${(event.total / 1024).toFixed(2)} KB)`);
        }
      };
      
      reader.onloadend = () => {
        const loadDuration = ((Date.now() - loadStartTime) / 1000).toFixed(2);
        const result = reader.result;
        
        console.group('🔍 [SD3.5] 验证生成的 Data URL');
        console.log('📄 Data URL 长度:', result ? result.length : 0);
        console.log('📄 Data URL 前缀:', result ? result.substring(0, 50) : 'null');
        console.log('📄 是否以 data: 开头:', result ? result.startsWith('data:') : false);
        console.log('📄 是否包含 base64,:', result ? result.includes('base64,') : false);
        console.log('⏱️ 读取耗时:', `${loadDuration} 秒`);
        
        // 验证 base64 数据
        if (result && result.includes('base64,')) {
          const base64Data = result.split('base64,')[1];
          console.log('📄 Base64 数据长度:', base64Data ? base64Data.length : 0);
          console.log('📄 Base64 数据前50字符:', base64Data ? base64Data.substring(0, 50) : 'null');
          console.log('📄 Base64 数据后50字符:', base64Data && base64Data.length > 50 ? base64Data.substring(base64Data.length - 50) : 'null');
          
          // 检查 base64 数据是否有效（只包含 base64 字符）
          const base64Regex = /^[A-Za-z0-9+/=]+$/;
          const isValidBase64 = base64Data ? base64Regex.test(base64Data) : false;
          console.log('📄 Base64 数据格式是否有效:', isValidBase64);
          
          // 检查数据长度是否合理（PNG 图片的 base64 通常至少几千字符）
          const isReasonableLength = base64Data && base64Data.length > 1000;
          console.log('📄 Base64 数据长度是否合理:', isReasonableLength, `(当前: ${base64Data ? base64Data.length : 0} 字符)`);
          
          if (!isValidBase64) {
            console.error('❌ [SD3.5] Base64 数据格式无效！');
            console.error('📄 无效字符位置:', base64Data ? base64Data.match(/[^A-Za-z0-9+/=]/) : 'null');
          }
          
          if (!isReasonableLength) {
            console.error('❌ [SD3.5] Base64 数据长度异常，可能被截断！');
            console.error('📄 完整 Base64 数据:', base64Data);
            console.error('📄 原始 Blob 大小:', `${(imageBlob.size / 1024).toFixed(2)} KB`);
            console.error('📄 预期 Base64 长度:', Math.ceil(imageBlob.size * 4 / 3), '字符');
            console.error('📄 实际 Base64 长度:', base64Data ? base64Data.length : 0, '字符');
          }
        }
        console.groupEnd();
        
        // 如果数据看起来不完整，抛出错误
        if (result && result.includes('base64,')) {
          const base64Data = result.split('base64,')[1];
          if (base64Data && base64Data.length < 1000) {
            const expectedLength = Math.ceil(imageBlob.size * 4 / 3);
            if (base64Data.length < expectedLength * 0.9) { // 允许 10% 的误差
              console.error('❌ [SD3.5] 错误：Base64 数据明显不完整！');
              console.error(`   预期长度: ${expectedLength} 字符`);
              console.error(`   实际长度: ${base64Data.length} 字符`);
              console.error(`   缺失: ${expectedLength - base64Data.length} 字符`);
              reject(new Error(`Base64 数据不完整：预期 ${expectedLength} 字符，实际 ${base64Data.length} 字符`));
              return;
            }
          }
        }
        
        resolve(result);
      };
      reader.onerror = (error) => {
        console.error('❌ [SD3.5] 读取图片数据失败:', error);
        console.error('📦 Blob 信息:', {
          type: imageBlob.type,
          size: imageBlob.size
        });
        console.error('📦 FileReader 错误:', reader.error);
        reject(new Error(`FileReader 读取失败: ${reader.error ? reader.error.message : '未知错误'}`));
      };
      
      console.log('📖 [SD3.5] 开始使用 FileReader 读取 Blob...');
      reader.readAsDataURL(imageBlob);
    });
    
    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000).toFixed(2);
    
    // 详细验证返回的数据
    console.group('🔍 [SD3.5] 最终数据验证');
    console.log('📄 imageData 类型:', typeof imageData);
    console.log('📄 imageData 长度:', imageData ? imageData.length : 0);
    console.log('📄 imageData 前100字符:', imageData ? imageData.substring(0, 100) : 'null');
    console.log('📄 imageData 后50字符:', imageData && imageData.length > 50 ? imageData.substring(imageData.length - 50) : 'null');
    
    if (imageData && imageData.includes('base64,')) {
      const base64Part = imageData.split('base64,')[1];
      console.log('📄 Base64 部分长度:', base64Part ? base64Part.length : 0);
      console.log('📄 Base64 部分前50字符:', base64Part ? base64Part.substring(0, 50) : 'null');
      console.log('📄 Base64 部分后50字符:', base64Part && base64Part.length > 50 ? base64Part.substring(base64Part.length - 50) : 'null');
      
      // 检查 base64 是否完整（应该是 4 的倍数，或末尾有 = 填充）
      if (base64Part) {
        const paddingCount = (base64Part.match(/=/g) || []).length;
        const isValidLength = base64Part.length % 4 === 0 || paddingCount > 0;
        console.log('📄 Base64 长度是否有效:', isValidLength, `(长度: ${base64Part.length}, 填充: ${paddingCount})`);
        
        if (!isValidLength && base64Part.length < 100) {
          console.error('❌ [SD3.5] 警告：Base64 数据可能不完整！');
          console.error('📄 完整 Base64 数据:', base64Part);
        }
      }
    }
    console.groupEnd();
    
    console.group('🎉 [SD3.5] 图片生成成功完成');
    console.log('🖼️ 图片文件名:', imageFilename);
    console.log('🔗 图片 URL:', imageUrl);
    console.log('📦 图片数据大小:', `${(imageData.length / 1024).toFixed(2)} KB`);
    console.log('⏱️ 总耗时:', `${duration} 秒`);
    console.log('⏰ 完成时间:', new Date().toISOString());
    console.groupEnd();
    
    // 同时输出到终端
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.error(`🎉 [SD3.5前端] 图片生成成功 [${new Date().toISOString()}]`);
    console.error(`   图片文件名: ${imageFilename}`);
    console.error(`   图片 URL: ${imageUrl}`);
    console.error(`   图片数据大小: ${(imageData.length / 1024).toFixed(2)} KB`);
    console.error(`   imageData 长度: ${imageData ? imageData.length : 0} 字符`);
    console.error(`   imageData 前100字符: ${imageData ? imageData.substring(0, 100) : 'null'}`);
    if (imageData && imageData.includes('base64,')) {
      const base64Part = imageData.split('base64,')[1];
      console.error(`   Base64 部分长度: ${base64Part ? base64Part.length : 0} 字符`);
      console.error(`   Base64 部分前50字符: ${base64Part ? base64Part.substring(0, 50) : 'null'}`);
      console.error(`   Base64 部分后50字符: ${base64Part && base64Part.length > 50 ? base64Part.substring(base64Part.length - 50) : 'null'}`);
    }
    console.error(`   总耗时: ${duration} 秒`);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    // 验证数据完整性
    if (!imageData || imageData.length < 100) {
      console.error('❌ [SD3.5] 错误：imageData 数据过短，可能不完整！');
      throw new Error(`图片数据不完整：长度仅 ${imageData ? imageData.length : 0} 字符`);
    }
    
    if (imageData.includes('base64,')) {
      const base64Part = imageData.split('base64,')[1];
      if (!base64Part || base64Part.length < 100) {
        console.error('❌ [SD3.5] 错误：Base64 数据过短，可能不完整！');
        throw new Error(`Base64 数据不完整：长度仅 ${base64Part ? base64Part.length : 0} 字符`);
      }
    }
    
    return {
      success: true,
      image_url: imageUrl,
      image_data: imageData,
      filename: imageFilename,
    };
  } catch (error) {
    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000).toFixed(2);
    
    console.group('❌ [SD3.5] 图片生成失败');
    const errorType = error.message?.includes('[服务器错误') ? '服务器端错误' : 
                      error.message?.includes('[网络错误') ? '网络错误' : 
                      error.message?.includes('[WebSocket错误') ? 'WebSocket错误' : 
                      '未知错误';
    console.error('🔴 错误类型:', errorType);
    console.error('📝 错误信息:', error.message);
    console.error('⏱️ 失败前耗时:', `${duration} 秒`);
    console.error('📚 错误堆栈:', error.stack);
    console.groupEnd();
    
    // 同时输出到终端
    logToTerminal.error(
      '图片生成失败',
      SD35_API_URL,
      `${errorType}: ${error.message}`,
      [
        `失败前耗时: ${duration} 秒`,
        '检查上述步骤的详细错误信息'
      ]
    );
    
    throw error;
  }
};

/**
 * 老照片修复功能
 * 使用 ComfyUI 接口进行老照片修复
 * @param {File} imageFile - 上传的老照片文件
 * @param {string} prompt - 优化指令（可选，默认: "high quality, sharp focus, clean skin"）
 * @returns {Promise<Object>} 返回修复结果 { image_url, image_data, filename }
 */
export const restoreOldPhoto = async (imageFile, prompt = "(masterpiece:1.2), (photorealistic:1.2), highly detailed face, realistic skin texture, sharp eyes, clean face, sharp focus, 8k") => {
  const startTime = Date.now();
  // 老照片修复使用独立的服务器地址
  const OLD_PHOTO_API_URL = getOldPhotoApiUrl();
  
  console.group('🖼️ [老照片修复] 开始处理');
  console.log('📁 图片文件:', imageFile.name);
  console.log('📝 优化指令:', prompt);
  console.log('🌐 API 地址:', OLD_PHOTO_API_URL);
  console.groupEnd();
  
  try {
    // 1. 上传图片到老照片修复服务器
    console.log('📤 [老照片修复] 上传图片...');
    const uploadImageToServer = async (file, apiUrl) => {
      const formData = new FormData();
      formData.append('image', file);
      const uploadUrl = `${apiUrl.replace(/\/$/, '')}/upload/image`;
      
      const response = await fetch(uploadUrl, {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        body: formData,
      });
      
      if (!response.ok) {
        const responseText = await response.text();
        throw new Error(`上传失败: ${response.status} ${response.statusText} - ${responseText}`);
      }
      
      const result = await response.json();
      return result.name || result.filename || result;
    };
    
    const uploadedImageName = await uploadImageToServer(imageFile, OLD_PHOTO_API_URL);
    
    if (!uploadedImageName || uploadedImageName === 'undefined') {
      throw new Error('上传图片失败：未获取到有效的文件名');
    }
    
    console.log('✅ [老照片修复] 图片上传成功:', uploadedImageName);
    
    // 2. 构建工作流 JSON（基于 sd35_oldpic2.json 模板，转换为标准 ComfyUI API 格式）
    // 根据 sd35_oldpic2.json 的结构构建工作流
    const seed = Math.floor(Math.random() * 1000000);
    
    const workflowJSON = {
      "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
          "ckpt_name": "sd3.5_large_turbo.safetensors"
        }
      },
      "2": {
        "class_type": "TripleCLIPLoader",
        "inputs": {
          "clip_name1": "clip_g.safetensors",
          "clip_name2": "clip_l.safetensors",
          "clip_name3": "t5xxl_fp8_e4m3fn.safetensors"
        }
      },
      "3": {
        "class_type": "LoadImage",
        "inputs": {
          "image": uploadedImageName
        }
      },
      "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
          "text": prompt,
          "clip": ["2", 0]
        }
      },
      "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {
          "text": "(scratches:1.4), (noise:1.4), blurry, deformed face, bad anatomy, low quality, artifacts, grainy",
          "clip": ["2", 0]
        }
      },
      "6": {
        "class_type": "VAEEncode",
        "inputs": {
          "pixels": ["3", 0],
          "vae": ["1", 2]
        }
      },
      "7": {
        "class_type": "KSampler",
        "inputs": {
          "seed": seed,
          "steps": 12,
          "cfg": 3.0,
          "sampler_name": "dpmpp_2m",
          "scheduler": "karras",
          "denoise": 0.45,
          "model": ["1", 0],
          "positive": ["4", 0],
          "negative": ["5", 0],
          "latent_image": ["6", 0]
        }
      },
      "8": {
        "class_type": "VAEDecode",
        "inputs": {
          "samples": ["7", 0],
          "vae": ["1", 2]
        }
      },
      "10": {
        "class_type": "FaceDetailer",
        "inputs": {
          "image": ["8", 0],
          "model": ["1", 0],
          "clip": ["2", 0],
          "vae": ["1", 2],
          "positive": ["4", 0],
          "negative": ["5", 0],
          "bbox_detector": ["11", 0]
        }
      },
      "11": {
        "class_type": "UltralyticsDetectorProvider",
        "inputs": {}
      },
      "12": {
        "class_type": "SaveImage",
        "inputs": {
          "filename_prefix": "OldPhoto_Restored",
          "images": ["10", 0]
        }
      }
    };
    
    console.log('📋 [老照片修复] 工作流 JSON 构建完成');
    console.log('📦 节点数量:', Object.keys(workflowJSON).length);
    
    // 3. 提交 prompt（使用自定义 API URL）
    console.log('📤 [老照片修复] 提交 prompt...');
    const submitPromptToServer = async (promptJSON, apiUrl) => {
      const promptUrl = `${apiUrl.replace(/\/$/, '')}/prompt`;
      const requestBody = { prompt: promptJSON };
      
      const response = await fetch(promptUrl, {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      if (!response.ok) {
        const responseText = await response.text();
        throw new Error(`提交失败: ${response.status} ${response.statusText} - ${responseText}`);
      }
      
      const result = await response.json();
      return result.prompt_id || result;
    };
    
    const promptId = await submitPromptForOldPhoto(workflowJSON);
    console.log('✅ [老照片修复] Prompt 提交成功，ID:', promptId);
    
    // 4. 轮询 history 接口获取结果（使用自定义 API URL）
    console.log('⏳ [老照片修复] 开始轮询结果...');
    
    const watchProgressOnServer = (promptId, apiUrl, onProgress, onComplete, onError, timeout = 5 * 60 * 1000) => {
      const historyUrl = `${apiUrl.replace(/\/$/, '')}/history/${promptId}`;
      const startTime = Date.now();
      
      return new Promise((resolve, reject) => {
        const poll = async () => {
          try {
            if (Date.now() - startTime > timeout) {
              const error = new Error('轮询超时');
              if (onError) onError(error);
              reject(error);
              return;
            }
            
            const response = await fetch(historyUrl, {
              method: 'GET',
              mode: 'cors',
              credentials: 'omit',
            });
            
            if (!response.ok) {
              throw new Error(`History 请求失败: ${response.status} ${response.statusText}`);
            }
            
            const history = await response.json();
            
            if (history[promptId]?.status?.completed) {
              // 查找 SaveImage 节点的输出（节点 12）
              const outputs = history[promptId].outputs;
              if (outputs && outputs["12"] && outputs["12"].images && outputs["12"].images.length > 0) {
                const filename = outputs["12"].images[0].filename || outputs["12"].images[0].name;
                if (onComplete) onComplete(filename);
                resolve(filename);
                return;
              }
            }
            
            // 如果还在处理中，继续轮询
            if (onProgress) {
              onProgress({ value: Date.now() - startTime, max: timeout });
            }
            
            setTimeout(poll, 2000); // 每 2 秒轮询一次
          } catch (error) {
            if (onError) onError(error);
            reject(error);
          }
        };
        
        poll();
      });
    };
    
    const imageFilename = await watchProgressOnServer(
      promptId,
      OLD_PHOTO_API_URL,
      (progress) => {
        if (progress.value !== undefined && progress.max !== undefined) {
          const progressPercent = Math.round((progress.value / progress.max) * 100);
          console.log(`📊 [老照片修复] 进度: ${progressPercent}%`);
        }
      },
      (filename) => {
        console.log('✅ [老照片修复] 修复完成:', filename);
      },
      (error) => {
        console.error('❌ [老照片修复] 修复失败:', error);
      },
      5 * 60 * 1000 // 5 分钟超时
    );
    
    // 5. 获取图片 URL 并转换为 base64（使用自定义 API URL）
    const imageUrl = `${OLD_PHOTO_API_URL}/view?filename=${imageFilename}`;
    console.log('📥 [老照片修复] 下载修复后的图片:', imageUrl);
    
    const imageResponse = await fetch(imageUrl, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
    });
    
    if (!imageResponse.ok) {
      throw new Error(`下载图片失败: ${imageResponse.status} ${imageResponse.statusText}`);
    }
    
    const imageBlob = await imageResponse.blob();
    const reader = new FileReader();
    
    return new Promise((resolve, reject) => {
      reader.onloadend = () => {
        const base64data = reader.result;
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        
        console.group('✅ [老照片修复] 处理完成');
        console.log('⏱️ 总耗时:', `${elapsed} 秒`);
        console.log('🖼️ 图片文件名:', imageFilename);
        console.groupEnd();
        
        resolve({
          image_url: imageUrl,
          image_data: base64data,
          filename: imageFilename
        });
      };
      
      reader.onerror = () => {
        reject(new Error('读取图片数据失败'));
      };
      
      reader.readAsDataURL(imageBlob);
    });
    
  } catch (error) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
    console.group('❌ [老照片修复] 处理失败');
    console.error('📝 错误信息:', error);
    console.error('⏱️ 失败前耗时:', `${elapsed} 秒`);
    console.groupEnd();
    throw error;
  }
};

// 保持向后兼容
export const submitPrompt = submitPromptForTextToImage;

export default {
  uploadImage,
  buildPromptJSON,
  submitPrompt,
  submitPromptForTextToImage,
  submitPromptForGroupPhoto,
  submitPromptForOldPhoto,
  watchProgress,
  getImageUrl,
  generateImage,
  restoreOldPhoto,
};
