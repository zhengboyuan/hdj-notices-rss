# 华东能源监管局通知公告 RSS

非官方公开公告归档。仅包含公开网站内容和采集代码，不包含任何内部知识库资料。

订阅地址：https://zhengboyuan.github.io/hdj-notices-rss/feed.xml

状态：https://zhengboyuan.github.io/hdj-notices-rss/status.json

每六小时由 GitHub Actions 尝试更新（实际运行可能延迟）。首次遍历官网现存全部分页，此后保留已采集记录；列表抓取失败时不覆盖之前的公开版本。

每条记录包含标题、原发布日期、唯一原文链接和摘要。正文及 PDF/Word/Excel 附件通过原文访问，本项目不保存正文及附件文件。尽量从详情页补齐截断的标题。

RSS 包含所有已归档公告，不限制为最近几条。阅读器是否导入全部历史记录由阅读器自身决定；不能将 RSS 条目数量等同于 Folo 实际入库数量。

本地运行：安装 requirements.txt 后执行 `python collect.py`。输出为 `data/notices.json`、`public/feed.xml` 和 `public/status.json`。
