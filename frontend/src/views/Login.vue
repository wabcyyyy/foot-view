<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-area">
        <h1 class="brand-logo">FOOT VIEW</h1>
        <p class="brand-slogan">专业 AI 步态分析平台</p>
      </div>

      <div class="form-container">
        <h2 class="form-title">
          <transition name="fade" mode="out-in">
            <span :key="isLoginMode">{{ isLoginMode ? '欢迎回来' : '创建新账号' }}</span>
          </transition>
        </h2>

        <div class="input-group">
          <input
            type="text"
            v-model="username"
            placeholder="用户名"
            @keyup.enter="handleAuth"
          />
        </div>

        <div class="input-group">
          <input
            type="password"
            v-model="password"
            placeholder="密码"
            @keyup.enter="handleAuth"
          />
        </div>

        <!-- 注册时的额外字段，带有高度过渡动画 -->
        <div class="expand-wrapper" :class="{ 'is-expanded': !isLoginMode }">
          <div class="input-group">
            <input
              type="password"
              v-model="confirmPassword"
              placeholder="确认密码"
              @keyup.enter="handleAuth"
              ref="confirmInput"
            />
          </div>
          <div class="input-group">
            <input
              type="email"
              v-model="email"
              placeholder="邮箱地址"
            />
          </div>
          <div class="input-group verification-group">
            <input
              type="text"
              v-model="verificationCode"
              placeholder="验证码"
              maxlength="6"
              @keyup.enter="handleAuth"
            />
            <button 
              class="send-code-btn" 
              @click="sendVerificationCode"
              :disabled="codeSending || countdown > 0"
            >
              {{ countdown > 0 ? `${countdown}s` : (codeSending ? '发送中...' : '获取验证码') }}
            </button>
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button class="auth-btn" @click="handleAuth" :disabled="loading">
          <transition name="fade" mode="out-in">
            <span :key="isLoginMode">{{ loading ? '处理中...' : (isLoginMode ? '登录' : '注册') }}</span>
          </transition>
        </button>

        <div class="toggle-mode">
          <span @click="toggleMode">
            {{ isLoginMode ? '没有账号？立即注册' : '已有账号？返回登录' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'Login',
  data() {
    return {
      username: '',
      password: '',
      confirmPassword: '',
      email: '',
      verificationCode: '',
      isLoginMode: true,
      loading: false,
      codeSending: false,
      countdown: 0,
      countdownTimer: null,
      error: ''
    };
  },
  methods: {
    toggleMode() {
      this.isLoginMode = !this.isLoginMode;
      this.error = '';
      // 清空输入框
      this.password = '';
      this.confirmPassword = '';
      this.email = '';
      this.verificationCode = '';
    },
    startCountdown() {
      this.countdown = 60;
      this.countdownTimer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(this.countdownTimer);
          this.countdownTimer = null;
        }
      }, 1000);
    },
    async sendVerificationCode() {
      this.error = '';

      if (!this.email) {
        this.error = '请输入邮箱地址';
        return;
      }

      // 简单的邮箱格式验证
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.email)) {
        this.error = '邮箱格式不正确';
        return;
      }

      this.codeSending = true;

      try {
        const response = await axios.post('/api/send-verification-code', {
          email: this.email
        });

        if (response.data.success) {
          this.startCountdown();
          this.error = '';
          alert('验证码已发送，请查收邮件');
        } else {
          this.error = response.data.message;
        }
      } catch (err) {
        this.error = '发送失败，请稍后重试';
        console.error(err);
      } finally {
        this.codeSending = false;
      }
    },
    async handleAuth() {
      this.error = '';

      if (!this.username || !this.password) {
        this.error = '请输入用户名和密码';
        return;
      }

      if (!this.isLoginMode) {
        if (this.password !== this.confirmPassword) {
          this.error = '两次输入的密码不一致';
          return;
        }
        if (!this.email) {
          this.error = '请输入邮箱地址';
          return;
        }
        if (!this.verificationCode) {
          this.error = '请输入验证码';
          return;
        }
      }

      this.loading = true;
      const endpoint = this.isLoginMode ? '/api/login' : '/api/register';

      try {
        const payload = {
          username: this.username,
          password: this.password
        };

        // 注册时添加邮箱和验证码
        if (!this.isLoginMode) {
          payload.email = this.email;
          payload.verification_code = this.verificationCode;
        }

        const response = await axios.post(endpoint, payload);

        if (response.data.success) {
          if (this.isLoginMode) {
            this.$router.push('/');
          } else {
            this.isLoginMode = true;
            this.error = '';
            alert('注册成功，请登录');
            this.username = '';
            this.password = '';
            this.confirmPassword = '';
            this.email = '';
            this.verificationCode = '';
          }
        } else {
          this.error = response.data.message;
        }
      } catch (err) {
        this.error = '请求失败，请稍后重试';
        console.error(err);
      } finally {
        this.loading = false;
      }
    }
  },
  beforeUnmount() {
    // 清除倒计时定时器
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  }
};
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f5f7;
  transition: background-color 0.5s;
}

.login-card {
  background: #ffffff;
  width: 100%;
  max-width: 400px;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  text-align: center;
  transition: all 0.3s ease;
}

.logo-area {
  margin-bottom: 20px;
}

.brand-logo {
  font-size: 24px;
  font-weight: 700;
  color: #1d1d1f;
  margin-bottom: 5px;
}

.brand-slogan {
  font-size: 14px;
  color: #86868b;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 10px;
  height: 27px; /* 固定高度防止跳动 */
  color: #333;
}

.input-group input {
  width: 100%;
  padding: 12px 15px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s;
  background-color: #fafafa;
}

.input-group input:focus {
  border-color: #000;
  background-color: #fff;
}

/* 展开动画容器 */
.expand-wrapper {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
}

.expand-wrapper.is-expanded {
  max-height: 220px; /* 足够容纳多个输入框的高度 */
  opacity: 1;
}

.expand-wrapper .input-group {
  margin-bottom: 12px;
}

.verification-group {
  display: flex;
  gap: 10px;
}

.verification-group input {
  flex: 1;
}

.send-code-btn {
  padding: 12px 16px;
  background-color: #333;
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  white-space: nowrap;
  transition: background-color 0.3s;
  min-width: 100px;
}

.send-code-btn:hover:not(:disabled) {
  background-color: #555;
}

.send-code-btn:disabled {
  background-color: #999;
  cursor: not-allowed;
}

.auth-btn {
  width: 100%;
  padding: 12px;
  background-color: #000;
  color: #fff;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  margin-top: 10px;
  transition: background-color 0.3s, transform 0.1s;
}

.auth-btn:hover:not(:disabled) {
  background-color: #333;
}

.auth-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.auth-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.toggle-mode {
  margin-top: 15px;
  font-size: 13px;
  color: #666;
}

.toggle-mode span {
  cursor: pointer;
  text-decoration: underline;
  transition: color 0.2s;
}

.toggle-mode span:hover {
  color: #000;
}

.error-msg {
  color: #d93025;
  font-size: 13px;
  margin-top: -5px;
  animation: shake 0.4s ease-in-out;
}

/* 文本淡入淡出动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}
</style>
