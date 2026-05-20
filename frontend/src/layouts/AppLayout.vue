<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="logo">📧 SmartMail</div>
      <nav class="nav">
        <router-link to="/chat" class="nav-item" active-class="active">🤖 邮箱智能助手</router-link>
        <router-link to="/" class="nav-item" exact-active-class="active">📧 邮件管理</router-link>
      </nav>
    </aside>
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}
.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #f8fafc 0%, #eff3f8 100%);
  color: #1e293b;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  box-shadow: 2px 0 12px rgba(0,0,0,0.05);
  border-right: 1px solid #e2e8f0;
}
.logo {
  font-size: 20px;
  font-weight: bold;
  padding: 0 20px 20px;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 20px;
  color: #3b82f6;
}
.nav-item {
  display: block;
  padding: 12px 20px;
  color: #475569;
  text-decoration: none;
  transition: all 0.2s;
  border-radius: 0 30px 30px 0;
  margin-right: 16px;
}
.nav-item:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.nav-item.active {
  background: #3b82f6;
  color: white;
  box-shadow: 0 2px 8px rgba(59,130,246,0.3);
}
.main-content {
  flex: 1;
  overflow-y: auto;
  background: #f8fafc;
}
</style>