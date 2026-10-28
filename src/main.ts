import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles/tokens.css'
import './styles/main.css'
import './styles/marketing.css'
import './styles/system.css'

createApp(App).use(router).mount('#app')
