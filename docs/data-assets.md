# 图片资产整理说明

## 来源

当前图片资产来源于项目根目录下的 Excel 文件：

- `命题三美甲评测数据（对外版）.xlsx`

该文件包含两张表：

- 表 1：手图 URL 与增强后款式图 URL 的配对关系。
- 表 2：原始款式图 URL 与增强后款式图 URL 的对应关系。

## 已生成文件

整理脚本：

- `scripts/prepare_image_assets.py`

生成的数据清单：

- `data/processed/image_pairs.csv`
- `data/processed/image_pairs.jsonl`
- `data/processed/tryon_pairs.csv`
- `data/processed/style_catalog.csv`
- `data/processed/image_assets.csv`
- `data/processed/image_inventory.csv`
- `data/processed/image_inventory_summary.json`
- `data/schemas/image-assets-schema.json`

## 图片目录

图片会按类型保存到：

- `data/raw/images/hands/`
- `data/raw/images/nail_styles_original/`
- `data/raw/images/nail_styles_enhanced/`

## 命名规则

手图：

```text
hand_001.png
hand_002.png
...
```

原始款式图：

```text
style_001_original.png
style_002_original.png
...
```

增强后款式图：

```text
style_001_enhanced.png
style_002_enhanced.png
...
```

## 当前状态

目前已经完成：

- Excel 到结构化清单的转换。
- 图片下载与本地归档。
- 图片尺寸、格式、缺失情况盘点。

当前资产统计：

- 手图：13 张，均为 `896x1200` PNG。
- 原始款式图：25 张，包含 PNG 和 JPG，尺寸不完全统一。
- 增强后款式图：25 张，均为 `896x1200` PNG。
- 可用于完整试戴验证的配对：13 组，见 `data/processed/tryon_pairs.csv`。
- 可用于商户策略和款式标签的款式：25 个，见 `data/processed/style_catalog.csv`。

如需重新生成清单，可执行：

```powershell
python scripts\prepare_image_assets.py
python scripts\audit_image_assets.py
```

## 数据原则

- 不创建大量额外测试样例。
- 不生成合成图片冒充真实数据。
- 如后续为了验证代码创建临时样例，应在验证完成后删除。
