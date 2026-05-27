# 数据目录

用于存放项目相关数据文件。

建议分类：

- `raw/`：原始数据。
- `processed/`：清洗后数据。
- `samples/`：样例数据。
- `schemas/`：字段结构和数据字典。

当前已有数据：

- `命题三美甲评测数据（对外版）.xlsx`

已整理出的结构化清单：

- `processed/image_pairs.csv`：手图与款式图配对关系。
- `processed/image_pairs.jsonl`：适合程序逐行读取的配对关系。
- `processed/tryon_pairs.csv`：可用于完整试戴验证的配对关系。
- `processed/style_catalog.csv`：款式标签和运营策略标注模板。
- `processed/image_assets.csv`：图片 URL、本地目标路径和下载状态。
- `processed/image_inventory.csv`：图片格式、尺寸、大小盘点。
- `processed/image_inventory_summary.json`：图片盘点摘要。
- `schemas/image-assets-schema.json`：图片资产整理说明。

图片文件目标目录：

- `raw/images/hands/`
- `raw/images/nail_styles_original/`
- `raw/images/nail_styles_enhanced/`
