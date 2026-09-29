# VisonCube 授权服务

独立 FastAPI 服务，复用现有账户服务验证登录令牌，只负责卡密、授权时长和推理租约。

## 安全边界

- 卡密由 `secrets` 生成 160 位随机数据；数据库只保存 `HMAC-SHA256`，不保存明文。
- 天卡、周卡、月卡分别增加 1、7、30 天。第一次兑换时开始计费；已有有效时长从原到期时间顺延。
- 同一用户重复提交同一卡密不会重复加时，其他用户无法再次使用。
- 管理权限在服务端校验。生产环境必须同时配置 `LICENSE_ADMIN_USERNAME` 和不可变的 `LICENSE_ADMIN_USER_ID`。
- 管理员身份未完整配置时，普通授权接口仍可启动，但 `/ready` 返回 503，所有管理接口拒绝访问。
- 推理客户端使用短期 ECDSA P-256/SHA-256 签名租约，可直接通过 Windows CNG 验证。私钥只留在服务器，客户端只内置公钥。
- 授权、卡密和管理响应均禁止代理或浏览器缓存；账户服务响应限制为 64 KiB。
- 日志和数据库不得记录卡密明文、登录令牌或签名私钥。

## 本地启动

1. 创建独立虚拟环境并安装 `requirements.txt`。
2. 复制 `.env.example` 的字段到服务管理器的环境配置，填入真实随机密钥。
3. 启动：

   ```text
   uvicorn app:create_app --factory --host 127.0.0.1 --port 8089
   ```

4. 将 Nginx 的 `/api/licenses/` 代理到 `127.0.0.1:8089`。

生产部署前必须先备份现有 Nginx、systemd 配置和授权数据库；先在备用端口完成健康检查，再切换反向代理。绝不能把 `.env`、数据库或私钥提交到 Git。

## 接口

- `GET /api/licenses/me`：当前账号授权状态。
- `POST /api/licenses/redeem`：兑换卡密。
- `POST /api/licenses/lease`：签发短期推理租约；无有效时长返回 403。
- `GET /api/licenses/admin/batches`：管理员查看最近批次。
- `POST /api/licenses/admin/batches`：管理员批量生成卡密，明文只在本次响应中返回。
- `GET /api/licenses/admin/overview`：管理员查看批次、卡密和授权统计。
- `GET /api/licenses/admin/batches/{batch_id}/codes`：分页查看批次内的卡密提示与状态，不返回卡密明文或哈希。
- `POST /api/licenses/admin/codes/{code_id}/revoke`：停用单个未兑换卡密；重复调用保持幂等。
- `POST /api/licenses/admin/batches/{batch_id}/revoke`：停用批次中全部未兑换卡密，不影响已兑换时长。
- `GET /api/licenses/admin/entitlements`：分页查看用户授权状态。
- `GET /api/licenses/admin/audit`：分页查看卡密生成、兑换和停用审计。
- `GET /api/licenses/public-key`：发布租约验签公钥；客户端发布时仍需固定公钥和 `key_id`。
- `GET /api/licenses/health`：进程存活检查。
- `GET /api/licenses/ready`：数据库与管理员身份配置就绪检查；不就绪时返回 503。

列表接口的 `limit` 和 `offset` 均由服务端限制范围。批次卡密接口可使用 `status=unused|redeemed|revoked` 筛选。停用接口可选请求体为 `{"reason":"原因"}`；不允许停用已兑换卡密，也不会扣减已兑换账户的剩余时长。

## 验证

在服务目录使用独立虚拟环境执行：

```text
python -m py_compile app.py
python -m pytest -q
```

部署切流前必须确认：`/health` 返回 200、`/ready` 返回 200、管理员本人能读取 `/admin/overview`、普通账户访问管理接口返回 403、AI 客户端能够依次读取 `/me` 并取得可通过固定公钥验证的 `/lease`。
