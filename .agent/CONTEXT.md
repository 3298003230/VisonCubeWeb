# VisonCubeWeb 项目上下文

## 项目目标

VisonCubeWeb 是 VisonCube 的统一官网和账户入口，展示首页、观山、听雨、逐风四个品牌页面，并在后续阶段复用现有 VisonCube 认证和发布服务。

## 当前状态

- 项目目录：`D:\Code\VisonCube\VisonCubeWeb`
- 当前为 Vue 3、TypeScript、Vite 工程，包含产品文档、设计规范、认证流程、首页和三个产品页。
- 已接入发布 API 并部署线上，主站地址为 `https://sjmf.xyz`。
- 页面命名：`首页`、`观山`（VisonCube-TV）、`听雨`（VisonCube-Music）、`逐风`（VisonCube-AI）。
- 默认入口为未登录状态：顶部只显示 `VisonCube` 和登录界面；产品导航与页面登录后才可见。
- 网站不显示软件图标或版本相关软件图片，只使用 VisonCube、观山、听雨、逐风名称及固定视觉语言。
- 参考方向：Raycast 的深色层级、紧凑导航、克制边框与产品演示方式；不得复制其品牌资产和页面结构。

## 原型预览

在 `prototype/` 目录运行：

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

然后访问 `http://127.0.0.1:4173/`。

添加 `?state=member` 仅用于预览登录后的产品主界面；再添加 `&page=guanshan`、`&page=tingyu` 或 `&page=zhufeng` 可预览三个产品页。`&release=loading` 或 `&release=error` 用于检查下载状态。

## 长期约束

- 网站账户复用现有 FastAPI 服务，不创建独立用户库。
- 前端不保存密码、SMTP 授权码和服务端密钥。
- 慢服务器环境下优先静态部署、按需加载和小体积首屏资源。
- VisonCube-AI 客户端登录接入已暂停，不影响“逐风”产品展示页设计。
