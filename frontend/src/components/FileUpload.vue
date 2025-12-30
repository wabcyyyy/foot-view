<template>
  <div class="file-upload">
    <input
      type="file"
      ref="fileInput"
      @change="onFileChange"
      accept="video/*"
      style="display: none"
    />

    <div class="upload-area" @click="triggerFileInput" :class="{ 'has-file': file, 'disabled': isUploading }">
      <div v-if="!file" class="placeholder">
        <span class="icon">+</span>
        <span class="text">点击选择视频文件</span>
      </div>
      <div v-else class="file-selected">
        <span class="icon-check">✓</span>
        <span class="filename">{{ file.name }}</span>
        <span class="change-text" v-if="!isUploading">点击更换</span>
      </div>
    </div>

    <!-- 进度条区域 -->
    <div v-if="isUploading" class="progress-section">
      <div class="progress-header">
        <span class="progress-stage">{{ progressStage }}</span>
        <span class="progress-percent" v-if="!isProcessing">{{ uploadProgress }}%</span>
      </div>
      <div class="progress-bar-container">
        <div 
          class="progress-bar" 
          :class="{ 'indeterminate': isProcessing }"
          :style="{ width: isProcessing ? '100%' : uploadProgress + '%' }"
        ></div>
      </div>
      <p class="progress-hint">{{ progressHint }}</p>
    </div>

    <button
      class="submit-btn"
      @click="upload"
      :disabled="!file || isUploading"
      :class="{ 'loading': isUploading }"
    >
      <span v-if="!isUploading">开始分析</span>
      <span v-else-if="!isProcessing">正在上传...</span>
      <span v-else>正在分析中...</span>
    </button>

    <p v-if="message" class="status-message" :class="{ error: isError }">{{ message }}</p>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      file: null,
      message: '',
      isUploading: false,
      isProcessing: false,
      isError: false,
      uploadProgress: 0
    };
  },
  computed: {
    progressStage() {
      if (this.isProcessing) {
        return '🔬 AI 分析中';
      }
      return '📤 上传视频';
    },
    progressHint() {
      if (this.isProcessing) {
        return '正在进行姿态检测和步态分析，请稍候...';
      }
      if (this.uploadProgress < 100) {
        return `已上传 ${this.formatFileSize(this.file.size * this.uploadProgress / 100)} / ${this.formatFileSize(this.file.size)}`;
      }
      return '上传完成，准备分析...';
    }
  },
  methods: {
    triggerFileInput() {
      if (!this.isUploading) {
        this.$refs.fileInput.click();
      }
    },
    onFileChange(e) {
      const selectedFile = e.target.files[0];
      if (selectedFile) {
        this.file = selectedFile;
        this.message = '';
        this.isError = false;
        this.uploadProgress = 0;
      }
    },
    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },
    async upload() {
      if (!this.file) return;

      this.isUploading = true;
      this.isProcessing = false;
      this.message = '';
      this.isError = false;
      this.uploadProgress = 0;

      const formData = new FormData();
      formData.append('video', this.file);

      try {
        const response = await axios.post('/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              // 上传完成后切换到处理阶段
              if (this.uploadProgress >= 100) {
                this.isProcessing = true;
              }
            }
          }
        });

        if (response.data.success) {
          this.$emit('upload-success', response.data.filename);
        } else {
          throw new Error(response.data.message || '上传失败');
        }
      } catch (error) {
        this.isError = true;
        this.message = error.message || '上传过程中发生错误';
        console.error(error);
        this.isUploading = false;
        this.isProcessing = false;
      }
    }
  }
};
</script>

<style scoped>
.file-upload {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-area {
  border: 2px dashed #e0e0e0;
  border-radius: 8px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: #fafafa;
}

.upload-area:hover:not(.disabled) {
  border-color: #999;
  background-color: #f5f5f5;
}

.upload-area.has-file {
  border-style: solid;
  border-color: #4caf50;
  background-color: #f0f9f0;
}

.upload-area.disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #888;
}

.placeholder .icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.file-selected {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #2e7d32;
}

.icon-check {
  font-size: 24px;
  margin-bottom: 5px;
}

.filename {
  font-weight: 500;
  margin-bottom: 5px;
  word-break: break-all;
}

.change-text {
  font-size: 12px;
  color: #666;
}

/* 进度条区域 */
.progress-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-stage {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
  font-family: 'SF Mono', monospace;
}

.progress-bar-container {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-bar.indeterminate {
  width: 100% !important;
  background: linear-gradient(
    90deg,
    #667eea 0%,
    #764ba2 25%,
    #667eea 50%,
    #764ba2 75%,
    #667eea 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite linear;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.progress-hint {
  font-size: 12px;
  color: #666;
  margin: 10px 0 0 0;
  text-align: center;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background-color: #000;
  color: #fff;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: background-color 0.3s;
}

.submit-btn:hover:not(:disabled) {
  background-color: #333;
}

.submit-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.submit-btn.loading {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.status-message {
  font-size: 13px;
  text-align: center;
  color: #666;
}

.status-message.error {
  color: #d32f2f;
}
</style>
