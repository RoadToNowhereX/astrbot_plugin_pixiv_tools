# astrbot_plugin_pixiv_tools

一座屎山，Antigravity的免费额度在上面自由自在地尽情拉屎。

适用于AstrBot的Pixiv插件，从[pixiv-mcp](https://github.com/DiLiuNEUexpresscompany/pixiv-mcp)和[astrbot_plugin_pixiv_reborn](https://github.com/vmoranv-reborn/astrbot_plugin_pixiv_reborn)项目迁移了重要功能。

使用前需要先获取PIXIV_REFRESH_TOKEN，获取方法请参考[Pixiv OAuth Flow](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)。

## 功能
以函数工具形式实现
- 自动刷新PIXIV_REFRESH_TOKEN
- 按标签和时间范围搜索小说
- 获取小说推荐
- 对获取到的结果按收藏数降序排序
- 将结果直接渲染为HTML卡片发送到AstrBot，可以在支持的前端上显示


