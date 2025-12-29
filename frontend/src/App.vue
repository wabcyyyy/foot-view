<template>
  <div id="app">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

:root {
  --text-primary: #1d1d1f;
  --text-secondary: #86868b;
  --bg-color: #f5f5f7;
  --card-bg: #ffffff;
  --accent-color: #000000;
  --primary-btn: #000000;
  --primary-btn-hover: #333333;
  --error-color: #d93025;
  --border-color: #e5e5e5;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: "PingFang SC", "Microsoft YaHei", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  background-color: var(--bg-color);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-weight: 400;
  line-height: 1.5;
  overflow-x: hidden;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  outline: none;
}

/* 页面过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.6s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
