/**
 * 老照片修复专用 API 函数
 * 使用独立的服务器地址：https://u486297-8ceb-89b88d1b.westc.gpuhub.com:8443
 * 基于 sd35_oldpic2.json 工作流
 */

const OLD_PHOTO_API_URL = "https://u486297-8ceb-89b88d1b.westc.gpuhub.com:8443";

/**
 * 上传图片到老照片修复服务器
 */
export const uploadImageToOldPhotoServer = async (file) => {
  const formData = new FormData();
  formData.append('image', file);
  const uploadUrl = `${OLD_PHOTO_API_URL}/upload/image`;
  
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

/**
 * 提交 prompt 到老照片修复服务器
 */
export const submitPromptToOldPhotoServer = async (promptJSON) => {
  const promptUrl = `${OLD_PHOTO_API_URL}/prompt`;
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

/**
 * 轮询老照片修复服务器获取结果
 */
export const watchOldPhotoProgress = async (promptId, onProgress, onComplete, onError, timeout = 5 * 60 * 1000) => {
  const historyUrl = `${OLD_PHOTO_API_URL}/history/${promptId}`;
  const startTime = Date.now();
  
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        if (Date.now() - startTime > timeout) {
          const error = new Error('轮询超时');
          onError(error);
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
            onComplete(filename);
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
        onError(error);
        reject(error);
      }
    };
    
    poll();
  });
};

/**
 * 获取图片 URL
 */
export const getOldPhotoImageUrl = (filename) => {
  return `${OLD_PHOTO_API_URL}/view?filename=${filename}`;
};
