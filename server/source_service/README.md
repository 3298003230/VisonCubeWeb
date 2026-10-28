# VisonCube 公共影像测试线路

这是一个与现有生产线路完全隔离的 FongMi `type: 4` 协议原型。它内置 Blender Foundation 开放短片，并可选择把 Internet Archive 的 NASA、FedFlix、Prelinger 和 Computer Chronicles 目录转换为客户端现有协议，用来验证自有线路的技术链路，不依赖闭源 Spider/JAR，也不提供弹幕。目录查询会先限制为包含 MPEG4 文件的条目，减少点开后不可播放的情况。

## 本地启动

使用 Python 3.11 或更高版本：

```powershell
python app.py --host 127.0.0.1 --port 8765
```

健康检查：

```text
http://127.0.0.1:8765/health
```

协议入口：

```text
http://127.0.0.1:8765/api/source
```

可直接作为点播配置导入的地址：

```text
http://127.0.0.1:8765/config.json
```

`site.example.json` 是单站点示例。Android 模拟器访问宿主机时需把其中的 `127.0.0.1` 改为 `10.0.2.2`；真机需要使用电脑在同一局域网内的 IP，并用 `--host 0.0.0.0` 启动。不要把这个测试配置合并到正式主备配置。

部署到反向代理后，应设置 `SOURCE_PUBLIC_API_URL` 为客户端实际可访问的完整 HTTPS API 地址，避免配置文件生成内部地址。服务器无法访问 Internet Archive 时可设置 `SOURCE_ENABLE_ARCHIVE=0`，此时首页、分类、搜索、详情和播放只使用内置开放短片，不会展示不可用的在线档案分类。

## 已实现入口

- 首页与分类页签；
- 分类分页；
- 标题搜索；
- 详情和 MP4 文件选择；
- 直连播放；
- 无弹幕模式。

服务对上游请求设置 8 秒超时和 4 MiB 响应上限。播放入口只接受本服务生成的 `https://archive.org/download/` 地址，避免把接口变成任意 URL 转发器。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试使用本地假数据，不访问网络。

## 限制

- 这是可行性原型，不是生产内容源；
- Internet Archive 在不同网络环境下的速度和可达性不受 VisonCube 控制；
- 目录中的条目由第三方上传，正式使用前必须进一步限定合集并审查每个条目的授权标记；
- 当前只选择可直接播放的 MP4，不处理 HLS、字幕、音轨或登录受限内容；
- 不缓存第三方响应，不适合直接承载大量客户端请求。
