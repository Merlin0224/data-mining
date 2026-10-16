# Pump it Up 水泵状态预测课程参考样例

使用 DrivenData 的坦桑尼亚水点数据，预测水泵的三种状态：正常运行、运行但需要维修、无法运行。项目包含数据探索、缺失与异常值处理、特征工程、分层交叉验证、模型比较、错误分析和比赛格式预测。

这是一份可复现的课程学习样例。所有结果均来自真实原始数据的本地验证，未提交至线上排行榜。

## 阅读入口

- [中文实验报告 PDF](output/pdf/Pump_it_Up_课程参考报告.pdf)
- [报告 HTML 源文件](课程参考报告.html)，下载后可离线打开。
- [已执行的中文 Notebook](Pump_it_Up_课程样例.ipynb)
- [各模型实际指标](results/model_comparison.csv)
- [各折交叉验证分数](results/cv_folds.csv)
- [结果一致性检查](results/audit.json)

## 复现

建议 Python 3.12，在独立虚拟环境中运行：

```bash
git clone https://github.com/Merlin0224/data-mining.git
cd data-mining
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python download_data.py
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 python pump_model.py --threads 4
python execute_notebook.py
python verify_outputs.py
```

Windows 激活环境使用 `.venv\Scripts\activate`，训练命令使用 `python pump_model.py --threads 4`。

Notebook 也可以逐节运行。仓库保留已执行的展示输出；首次重新运行时，如果原始数据或完整实验文件不存在，会下载数据并重新训练。计算仅使用 CPU，每个模型最多 4 线程。

## 数据与实验设计

训练特征包含 59,400 条记录，39 个预测字段和 `id`，标签单独存放；无标签测试集为 14,850 条。原始数据从 DrivenData 自有公开 S3 存储下载，提交模板来自 DrivenData 官方代码仓库。文件来源、行数和 SHA-256 见 [manifest.json](data/raw/manifest.json)。

先按类别分层划分 80% 开发集和 20% 保留验证集，随机种子固定为 42。只在开发集内部进行三折交叉验证，按平均 Accuracy 选择模型；同时报告 Macro-F1 和各类别召回率。验证集不用于选参、预处理拟合或早停。

候选模型为多数类基线、逻辑回归、随机森林，以及深度 6/8 的两组 CatBoost。特征包括泵龄、记录年月、零值标记和数值对数变换。逻辑回归和随机森林的中位数填补、标准化与低频类别编码均在 Pipeline 内按训练折拟合；CatBoost 接收原生类别字段。

参数固定后，在全部带标签数据上重训，按官方模板的 `id` 顺序生成 `results/submission.csv`。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `download_data.py` | 下载原始数据与官方模板，记录来源和哈希 |
| `pump_model.py` | 特征工程、训练内部 CV、独立验证、全量重训与预测 |
| `execute_notebook.py` | 使用项目内核配置执行 Notebook |
| `verify_outputs.py` | 核对标签对齐、数据切分、指标、提交顺序及模型复现 |
| `predict_saved.py` | 加载训练后生成的 CatBoost 原生模型进行预测 |
| `build_report.py` | 根据实际结果生成中文 PDF 和 HTML 报告 |
| `requirements.txt` | 固定主要运行依赖 |
| `requirements-lock.txt` | 记录本次服务器的完整实测依赖 |
| `results/` | 模型比较、逐折结果、分类报告、图表与提交预测 |

原始数据、大型模型文件和包含原始特征的逐条错误数据不纳入 Git，运行脚本即可生成。报告文件随仓库提供；修改实验后，安装可选的 `reportlab` 并运行 `python build_report.py` 重新生成报告。

## 结果解释

| 模型 | 开发集三折 CV Accuracy | 保留验证集 Accuracy | 保留验证集 Macro-F1 |
| --- | ---: | ---: | ---: |
| 多数类基线 | 0.5431 | 0.5431 | 0.2346 |
| 逻辑回归 | 0.7630 | 0.7699 | 0.6210 |
| 随机森林 | 0.7988 | 0.8047 | 0.6579 |
| CatBoost 深度 6 | 0.8011 | 0.8051 | 0.6737 |
| CatBoost 深度 8 | **0.8043** | **0.8109** | **0.6819** |

最佳配置依据开发集内部 CV 选择。表中为本地验证分数，未取得线上排行榜分数。
最佳配置对“运行但需维修”类的验证 Recall 为 **0.2827**，仍会漏掉不少维修样本。

“运行但需维修”类别占比较低，应结合 Macro-F1、各类 Recall 和混淆矩阵评估，避免只看总体 Accuracy。随机分层验证不能证明跨地区或跨年份的泛化能力。特征重要性表示模型关联，不能解释为因果效应。详细结果及局限见报告。

## 来源

- [DrivenData 题目和字段说明](https://www.drivendata.org/competitions/7/pump-it-up-data-mining-the-water-table/page/25/)
- [官方对课程项目使用数据的说明](https://community.drivendata.org/t/use-the-dataset-for-a-class-project/5836)
- [DrivenData 官方提交模板](https://github.com/drivendataorg/pump-it-up/blob/master/data/submission_format.csv)
- [scikit-learn 防止数据泄漏](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage)
- [CatBoost 类别特征文档](https://catboost.ai/docs/en/features/categorical-features)
