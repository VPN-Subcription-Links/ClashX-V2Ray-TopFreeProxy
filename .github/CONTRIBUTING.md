# Contributing

## Proposing Changes

Use issues for bugs or suggestions and pull requests for changes. Describe the problem, the resulting behavior, and relevant validation. Keep changes focused and update affected documentation.

## Subscription Changes

Edit sources in `combine/sources.json`, then run `python -m combine.sources` from the repository root. Verify replacement feeds before enabling them. Preserve every removed or replaced link in the affected guides' `<!-- Archived Reference:` blocks. Fetching and parsing do not establish node connectivity.

For code or source changes, run:

```sh
python -m unittest discover -s combine/tests -v
python -m combine.sources --check
```

See the [maintenance guide](../docs/maintenance.md) for environment setup, live refreshes, and client-engine validation. Documentation-only changes should check links and formatting.

## Project Policies

Follow the [code of conduct](CODE_OF_CONDUCT.md) and the [noncommercial license](../LICENSE.md). Report security vulnerabilities privately according to the [security policy](SECURITY.md).

---

# 贡献指南

## 提出修改

通过 Issue 反馈问题或建议，通过 Pull Request 提交修改。说明问题、修改后的行为及相关验证结果。保持修改范围明确，并更新受影响的文档。

## 订阅修改

在 `combine/sources.json` 中编辑来源，然后从仓库根目录运行 `python -m combine.sources`。启用替换来源前请验证订阅内容。删除或替换的每个链接都必须保留在对应教程的 `<!-- Archived Reference:` 归档列表中。获取与解析成功不代表节点可连接。

修改代码或来源时，请运行：

```sh
python -m unittest discover -s combine/tests -v
python -m combine.sources --check
```

环境设置、在线刷新及客户端引擎验证见[维护指南](../docs/maintenance.md)。仅修改文档时，请检查链接与格式。

## 项目政策

请遵守[行为准则](CODE_OF_CONDUCT.md)及[非商业使用许可](../LICENSE.md)。安全漏洞请按照[安全政策](SECURITY.md)私下报告。
