<template>
  <div class="file-upload">
    <input
      type="file"
      ref="fileInput"
      @change="onFileChange"
      accept="video/*"
      style="display: none"
    />

    <div class="upload-area" @click="triggerFileInput" :class="{ 'has-file': file }">
      <div v-if="!file" class="placeholder">
        <span class="icon">+</span>
        <span class="text">点击选择视频文件</span>
      </div>
      <div v-else class="file-selected">
        <span class="icon-check">✓</span>
        <span class="filename">{{ file.name }}</span>
        <span class="change-text">点击更换</span>
      </div>
    </div>

    <button
      class="submit-btn"
      @click="upload"
      :disabled="!file || isUploading"
      :class="{ 'loading': isUploading }"
    >
      <span v-if="!isUploading">开始分析</span>
      <span v-else>正在上传并分析...</span>
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
      isError: false
    };
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
      }
    },
    async upload() {
      if (!this.file) return;

      this.isUploading = true;
      this.message = '';
      this.isError = false;

      const formData = new FormData();
      formData.append('video', this.file);

      try {
        const response = await axios.post('/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
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

.upload-area:hover {
  border-color: #999;
  background-color: #f5f5f5;
}

.upload-area.has-file {
  border-style: solid;
  border-color: #4caf50;
  background-color: #f0f9f0;
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

.status-message {
  font-size: 13px;
  text-align: center;
  color: #666;
}

.status-message.error {
  color: #d32f2f;
}
</style>
