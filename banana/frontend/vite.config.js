import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync, writeFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

// ES modules 中获取 __dirname 的替代方法
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// 注意：现在不再需要构建时替换，build-info.js 中直接使用 Date.now()
// 每次构建时，由于文件被重新读取，Date.now() 会生成新的值
console.log('🔨 构建开始时间:', new Date().toISOString())

export default defineConfig({
  plugins: [
    react(),
    // 不再需要自定义插件，build-info.js 中直接使用 Date.now()
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // SD3.5 代理配置（现在指向远程 HTTPS 服务器）
      '/sd35': {
        target: 'https://u486297-a278-e279861b.westb.seetacloud.com:8443',
        changeOrigin: true,
        secure: false, // 开发环境：忽略 HTTPS 证书验证（如果服务器使用自签名证书）
        ws: true, // 支持 WebSocket（会自动使用 WSS）
        rewrite: (path) => {
          const newPath = path.replace(/^\/sd35/, '');
          console.log(`🔄 [SD3.5代理] 路径重写: ${path} -> ${newPath}`);
          return newPath;
        },
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            console.error('❌ [SD3.5代理] 代理错误:', {
              message: err.message,
              code: err.code,
              url: req?.url,
              method: req?.method,
              timestamp: new Date().toISOString()
            });
          });
          
          proxy.on('proxyReq', (proxyReq, req, res) => {
            const timestamp = new Date().toISOString();
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log(`📤 [SD3.5代理] 请求开始 [${timestamp}]`);
            console.log(`   方法: ${req.method}`);
            console.log(`   原始URL: ${req.url}`);
            console.log(`   代理路径: ${proxyReq.path}`);
            console.log(`   目标地址: ${proxyReq.getHeader('host')}${proxyReq.path}`);
            console.log(`   请求头:`, {
              'content-type': proxyReq.getHeader('content-type'),
              'content-length': proxyReq.getHeader('content-length'),
              'user-agent': proxyReq.getHeader('user-agent')?.substring(0, 50) + '...'
            });
            
            // 如果是 POST/PUT 请求，尝试记录请求体大小
            if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
              const contentType = proxyReq.getHeader('content-type') || '';
              if (contentType.includes('multipart/form-data')) {
                console.log(`   请求体: FormData (multipart/form-data)`);
              } else if (contentType.includes('application/json')) {
                // JSON 请求体大小
                const contentLength = proxyReq.getHeader('content-length');
                if (contentLength) {
                  console.log(`   请求体大小: ${(parseInt(contentLength) / 1024).toFixed(2)} KB`);
                }
              }
            }
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          });
          
          proxy.on('proxyRes', (proxyRes, req, res) => {
            const timestamp = new Date().toISOString();
            const statusCode = proxyRes.statusCode;
            const statusText = proxyRes.statusMessage || '';
            const isError = statusCode >= 400;
            
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            if (isError) {
              console.error(`❌ [SD3.5代理] 响应错误 [${timestamp}]`);
            } else {
              console.log(`📥 [SD3.5代理] 响应成功 [${timestamp}]`);
            }
            console.log(`   URL: ${req.url}`);
            console.log(`   状态码: ${statusCode} ${statusText}`);
            console.log(`   响应头:`, {
              'content-type': proxyRes.headers['content-type'],
              'content-length': proxyRes.headers['content-length'],
              'server': proxyRes.headers['server']
            });
            
            // 收集响应体（用于错误情况）
            if (isError) {
              let responseBody = '';
              const chunks = [];
              
              proxyRes.on('data', (chunk) => {
                chunks.push(chunk);
              });
              
              proxyRes.on('end', () => {
                try {
                  responseBody = Buffer.concat(chunks).toString('utf8');
                  const preview = responseBody.length > 500 
                    ? responseBody.substring(0, 500) + '...' 
                    : responseBody;
                  console.error(`   错误响应体:`, preview);
                  
                  // 尝试解析 JSON 错误信息
                  try {
                    const errorData = JSON.parse(responseBody);
                    console.error(`   错误详情:`, errorData);
                  } catch (e) {
                    // 不是 JSON，直接显示文本
                  }
                } catch (e) {
                  console.error(`   无法读取响应体:`, e.message);
                }
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
              });
            } else {
              const contentLength = proxyRes.headers['content-length'];
              if (contentLength) {
                console.log(`   响应体大小: ${(parseInt(contentLength) / 1024).toFixed(2)} KB`);
              }
              console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            }
          });
          
          // WebSocket 连接日志
          proxy.on('open', (proxySocket) => {
            console.log('🔌 [SD3.5代理] WebSocket 连接已建立');
          });
          
          proxy.on('close', (res, socket, head) => {
            console.log('🔌 [SD3.5代理] WebSocket 连接已关闭');
          });
          
          proxy.on('error', (err, req, socket) => {
            console.error('❌ [SD3.5代理] WebSocket 错误:', {
              message: err.message,
              code: err.code,
              url: req?.url
            });
          });
        },
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'esbuild', // 使用 esbuild 替代 terser，更快且不需要额外依赖
    // 禁用构建缓存，确保每次都是全新构建
    // 注意：这会禁用 Vite 的依赖预构建缓存，但确保每次都重新计算 hash
    // 启用缓存破坏（cache busting）- 使用更短的哈希但确保每次都不同
    rollupOptions: {
      output: {
        // 为文件名添加哈希，确保缓存破坏
        // 使用 [hash:8] 生成 8 位哈希，每次构建都不同
        entryFileNames: 'assets/[name]-[hash:8].js',
        chunkFileNames: 'assets/[name]-[hash:8].js',
        assetFileNames: 'assets/[name]-[hash:8].[ext]',
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'i18n-vendor': ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
        },
      },
    },
    // 确保每次构建都生成新的哈希
    emptyOutDir: true,
    // 禁用 chunk 大小警告，因为我们使用手动 chunk
    chunkSizeWarningLimit: 1000,
  },
})




