"""Build a Chinese PDF/HTML report from measured experiment outputs."""
from pathlib import Path
import base64
import csv
import html
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, Image, PageBreak, KeepTogether, Preformatted)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
PDF_DIR = ROOT / 'output/pdf'
PDF_DIR.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts/simsun.ttc')
if FONT.exists():
    pdfmetrics.registerFont(TTFont('Chinese', str(FONT), subfontIndex=0))
else:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    # Server fallback if reportlab and a CJK font are separately available.
    pdfmetrics.registerFontFamily('Chinese', normal='STSong-Light')
    FONT = None
BODY_FONT = 'Chinese' if FONT else 'STSong-Light'
style = ParagraphStyle('Body', fontName=BODY_FONT, fontSize=10.2, leading=16.2,
                       textColor=colors.HexColor('#263b4d'), spaceAfter=7, wordWrap='CJK')
title_style = ParagraphStyle('Title', parent=style, fontSize=22, leading=31, spaceAfter=12,
                             textColor=colors.HexColor('#126c65'))
h_style = ParagraphStyle('Heading', parent=style, fontSize=15.5, leading=23,
                         spaceBefore=2, spaceAfter=10, textColor=colors.HexColor('#126c65'))
small_style = ParagraphStyle('Small', parent=style, fontSize=8.5, leading=12.8, spaceAfter=6)
cell_style = ParagraphStyle('Cell', parent=style, fontSize=8.3, leading=12, spaceAfter=0)
code_style = ParagraphStyle('Code', fontName='Courier', fontSize=8.0, leading=12,
                            backColor=colors.HexColor('#edf4f5'), borderPadding=8, spaceAfter=9)
story, web = [], []
metadata = json.loads((OUT / 'run_metadata.json').read_text())
audit = json.loads((OUT / 'audit.json').read_text())
report = json.loads((OUT / 'classification_report.json').read_text())


def read_csv(name):
    with (OUT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


comparison = read_csv('model_comparison.csv')
best = next(r for r in comparison if r['model'] == metadata['selected_model'])
majority = next(r for r in comparison if r['model'] == 'majority')
labels = ['functional', 'functional needs repair', 'non functional']
counts = audit['all_label_counts']


def p(text, small=False):
    story.append(Paragraph(escape(text), small_style if small else style))
    web.append('<p>' + html.escape(text) + '</p>')


def heading(text, first=False):
    if not first:
        story.append(PageBreak())
        web.append('</section>')
    web.append('<section>')
    story.append(Paragraph(escape(text), title_style if first else h_style))
    web.append('<h1>' + html.escape(text) + '</h1>')


def table(headers, rows, widths):
    data = [[Paragraph(escape(str(c)), cell_style) for c in row] for row in [headers] + rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dcefed')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f7f9')]),
        ('LINEBELOW', (0, 0), (-1, 0), 0.7, colors.HexColor('#84b3ae')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.extend([t, Spacer(1, 10)])
    web.append('<table><thead><tr>' + ''.join('<th>' + html.escape(str(c)) + '</th>' for c in headers)
               + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + html.escape(str(c)) + '</td>'
               for c in row) + '</tr>' for row in rows) + '</tbody></table>')


def fig(filename, caption, width=470, height=None):
    path = OUT / 'figures' / filename
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    height = height or width * h / w
    image = Image(str(path), width=width, height=height)
    image.hAlign = 'CENTER'
    story.append(KeepTogether([image, Spacer(1, 3), Paragraph(escape(caption), small_style)]))
    b64 = base64.b64encode(path.read_bytes()).decode()
    web.append(f'<figure><img src="data:image/png;base64,{b64}"/><figcaption>{html.escape(caption)}</figcaption></figure>')


heading('Pump it Up：水泵状态预测', first=True)
p('课程作业参考样例 | 真实公开数据实验 | 2026-10-16', small=True)
p(f"本项目使用坦桑尼亚水点数据，将水泵状态分为正常、运行但需维修、无法运行三类。"
  f"在 47,520 条开发样本内进行三折交叉验证，选中 {metadata['selected_model']}；"
  f"其在 11,880 条保留验证样本上的 Accuracy 为 {float(best['validation_accuracy']):.4f}，"
  f"Macro-F1 为 {float(best['validation_macro_f1']):.4f}。随后使用全部 59,400 条带标签样本重训，"
  '生成 14,850 条测试预测。没有提交至比赛网站，线上分数未知。')
table(['数据部分', '样本数', '用途'], [
    ['带标签数据', '59,400', '原始 39 个预测字段及 id，目标另存于标签表'],
    ['开发集', '47,520', '模型拟合；内部三折交叉验证选择候选配置'],
    ['保留验证集', '11,880', '参数固定后的本地泛化评估'],
    ['无标签测试集', '14,850', '全量重训后生成比赛格式预测'],
], [94, 64, 326])
p('任务价值在于帮助识别需要检查和维修的水点。模型输出是历史记录条件下的状态分类，'
  '不是未来故障时间、维修成本或因果影响的估计。[1]')
fig('class_distribution.png', '图 1  开发集类别分布；需维修类明显少于另外两类。', width=450)
p('全部带标签数据中的类别计数：' + '；'.join(f'{k}: {counts[k]:,}' for k in labels) + '。', small=True)

heading('2  数据质量与特征处理')
quality = read_csv('data_quality.csv')
table(['字段', '开发集缺失率', '处理方式'], [[r.get('', ''), f"{float(r['missing_rate']):.2%}",
    '删除高基数名称列' if r.get('', '') == 'scheme_name' else '保留并使用缺失标记']
    for r in quality[:5]], [139, 98, 247])
p('空值并不是唯一的数据质量问题。建造年份为 0、晚于记录年份的建造年份，以及接近 0 的经纬度，'
  '分别按无效年份和本数据中的无效坐标处理。海拔、人口和 amount_tsh 中的 0 没有被统一当成缺失。')
p('数值特征增加泵龄、记录年/月、人口与 amount_tsh 的 log1p、部分零值标记；'
  '地区和区县代码按类别处理，并组合成地区内区县标识。类别文本只统一大小写和首尾空格，'
  '缺失值使用独立字符串。amount_tsh 按官方的静水头相关字段使用，不把它解释为水费。[1]')
p(f"为控制复杂度，预先删除 id、记录者、水点名称、方案名称及部分重复层级列；工程后保留 "
  f"{audit['clean_feature_count']} 个字段。该规则是教学设计，并没有通过本例证明为最优特征子集。")
fig('quantity_status.png', '图 2  开发集内不同水量类别的状态比例；每行比例之和为 1。', width=450)
p('图中关联不能单独证明因果关系，也不能直接推导实际维修优先级。', small=True)

heading('3  模型、选择标准与实验结果')
p('多数类模型给出最低比较基准；逻辑回归提供线性基线；随机森林学习非线性交互；'
  'CatBoost 使用原生类别字段，避免为其预先做 One-Hot。[4] 所有比较使用同一个分层切分，随机种子均为 42。')
p('固定配置：逻辑回归 C=1、lbfgs、最多 1500 次迭代；随机森林 240 棵树、'
  'min_samples_leaf=2、max_features=sqrt；CatBoost 分别为深度 6/650 轮和深度 8/850 轮，'
  '学习率均为 0.07。CatBoost 不使用保留验证集进行早停。')
p('逻辑回归和随机森林使用折内中位数填补与缺失指示、数值标准化，以及 One-Hot 类别编码；'
  'One-Hot 的低频阈值为 10，每列最多 200 个输出类别。CatBoost 接收数值缺失和字符串类别。'
  '所有可学习处理均在训练折拟合，符合 Pipeline 防止泄漏的做法。[3]')
table(['模型', 'CV Accuracy', 'CV 标准差', '验证 Accuracy', '验证 Macro-F1'], [
    [r['model'], f"{float(r['cv_accuracy_mean']):.4f}", f"{float(r['cv_accuracy_std']):.4f}",
     f"{float(r['validation_accuracy']):.4f}", f"{float(r['validation_macro_f1']):.4f}"] for r in comparison
], [126, 89, 80, 94, 95])
fig('model_comparison.png', '图 3  选择依据为开发集三折平均 Accuracy；误差棒为折间样本标准差，不是置信区间。', width=470)

heading('4  最终验证与错误分析')
p(f"CV 选中的 {metadata['selected_model']} 在验证集上的 Accuracy 为 "
  f"{float(best['validation_accuracy']):.4f}，比多数类基线高 "
  f"{(float(best['validation_accuracy'])-float(majority['validation_accuracy']))*100:.2f} 个百分点。"
  f"Macro-F1 为 {float(best['validation_macro_f1']):.4f}。Accuracy=正确预测数/总样本数；"
  'Macro-F1 为三类 F1 的等权平均。两个指标应同时查看。')
p(f"该配置在开发集上的拟合准确率为 {float(best['train_accuracy']):.4f}，"
  f"高于保留验证集约 {(float(best['train_accuracy'])-float(best['validation_accuracy']))*100:.2f} 个百分点。"
  '训练分数更高并不代表对新样本同样准确。')
table(['类别', 'Precision', 'Recall', 'F1', '样本数'], [
    [k, f"{report[k]['precision']:.4f}", f"{report[k]['recall']:.4f}",
     f"{report[k]['f1-score']:.4f}", f"{int(report[k]['support']):,}"] for k in labels
], [160, 83, 83, 78, 80])
fig('confusion_matrix.png', '图 4  验证集混淆矩阵：行是真实状态，列是预测状态，数字是样本数。', width=405)
repair = report['functional needs repair']
p(f"需维修类的 Recall={repair['recall']:.4f}，即真实需维修的水点中约 "
  f"{repair['recall']*100:.1f}% 被识别为该类。少数类仍有漏检风险。"
  '逐行错误样本保存在 results/errors.csv，可按地区、水量和水泵类型进一步检查误差分布。')

heading('5  模型解释、局限与改进')
importance_path = OUT / 'feature_importance.csv'
if importance_path.exists():
    importance = read_csv('feature_importance.csv')
    p('开发阶段模型的重要性靠前字段为：' + '、'.join(r['feature'] for r in importance[:5]) + '。'
      '下图为 CatBoost 的 PredictionValuesChange 重要性，用于解释模型依赖哪些字段；'
      '相关或重复特征会分摊重要性，因此不应把该排序解释为因果效应或业务收益。')
    fig('feature_importance.png', '图 5  开发集拟合模型的前 15 个特征重要性。', width=420)
p('地理泛化：随机分层切分保留类别比例，但邻近地区可能同时出现在开发集和验证集。'
  '若目标是部署到从未出现的地区，应另做按 region 或地理网格分组验证。本次未执行该实验。')
p('类别权衡：需维修类样本少，可在训练内部比较类别权重、阈值或重采样策略；'
  '这些策略可能改善少数类召回，也可能降低总 Accuracy，必须先明确评价目标。')
p('实验预算：这里只比较五组预先设定配置，各算法没有经过等预算的充分调参；'
  '当前结果只支持这几组配置的比较。未来可增加折数、训练内部搜索或保留新的最终测试集。')
p('时效与解释：这些历史横截面特征只能支持相近采样条件下的状态分类。'
  '本地结果不代表线上分数，不能证明跨年份表现，也不能替代实地检查。')

heading('6  复现、交付文件与参考来源')
p('本实验在实验室服务器的独立项目虚拟环境内运行。以下命令在项目根目录执行。'
  '训练仅用 CPU，模型线程数最多为 4；依赖版本、切分 ID、逐折分数和原始文件校验信息都已保存。')
commands = '''.venv/bin/python download_data.py
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 \\
  .venv/bin/python pump_model.py --threads 4
.venv/bin/python execute_notebook.py
.venv/bin/python verify_outputs.py'''
story.append(Preformatted(commands, code_style))
web.append('<pre>' + html.escape(commands) + '</pre>')
table(['文件', '用途'], [
    ['Pump_it_Up_课程样例.ipynb', '已执行，含中文讲解、数据分析、图表与结果'],
    ['pump_model.py / requirements.txt', '模型代码和固定的顶层依赖版本'],
    ['data/raw/manifest.json', 'DrivenData 原始公开链接、文件大小及 SHA-256'],
    ['results/model_comparison.csv / cv_folds.csv', '模型比较与每一折的实际分数'],
    ['results/validation_predictions.csv / errors.csv', '逐条验证预测与错误样本'],
    ['results/submission.csv', '全量重训后的 14,850 条测试预测'],
    ['results/audit.json / run_metadata.json', '核对结果与执行环境记录'],
], [248, 236])
p('提交说明：模板来自 DrivenData 官方代码仓库，其全部 14,850 个 ID 和顺序已与原始测试集核对。[6] '
  '脚本按模板 ID 对齐预测。未登录比赛账号、未上传预测。'
  'final_model.cbm 为全量模型，重新使用时需要先调用配套 PumpFeatures 转换原始特征。', small=True)
p('复核通过：原始文件哈希、打乱标签后的 id 对齐、验证切分、逐行指标重算、混淆矩阵总量、'
  '交叉验证选择规则、模板打乱排序，以及保存模型对全部测试预测的复现。', small=True)
sources = [
    ('[1] DrivenData：任务、原始字段和提交格式', 'https://www.drivendata.org/competitions/7/pump-it-up-data-mining-the-water-table/page/25/'),
    ('[2] DrivenData：数据可用于课程项目的官方说明', 'https://community.drivendata.org/t/use-the-dataset-for-a-class-project/5836'),
    ('[3] scikit-learn：Data leakage 与 Pipeline', 'https://scikit-learn.org/stable/common_pitfalls.html#data-leakage'),
    ('[4] CatBoost：Categorical features', 'https://catboost.ai/docs/en/features/categorical-features'),
    ('[5] Bull, Slavitt, Lipstein (2016): Harnessing the Power of the Crowd to Increase Capacity for Data Science in the Social Sector', 'https://arxiv.org/abs/1606.07781'),
    ('[6] DrivenData 官方仓库：submission_format.csv', 'https://github.com/drivendataorg/pump-it-up/blob/master/data/submission_format.csv'),
]
for label, url in sources:
    story.append(Paragraph(f'<link href="{escape(url)}" color="#126c65">{escape(label)}</link>', small_style))
    web.append(f'<p><a href="{html.escape(url)}">{html.escape(label)}</a></p>')
web.append('</section>')


def page_frame(canvas, doc):
    w, h = A4
    canvas.setStrokeColor(colors.HexColor('#c8dedc'))
    canvas.line(44, h - 33, w - 44, h - 33)
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(colors.HexColor('#617781'))
    canvas.drawString(44, h - 25, 'Pump it Up | 课程作业参考样例')
    canvas.drawRightString(w - 44, 24, f'{doc.page}')


pdf_path = PDF_DIR / 'Pump_it_Up_课程参考报告.pdf'
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=46, leftMargin=46,
                         topMargin=48, bottomMargin=42,
                         title='Pump it Up 水泵状态预测：课程参考报告', author='课程参考样例')
doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
css = '''body{margin:0;background:#edf3f5;color:#263b4d;font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:1000px;margin:auto;background:white;padding:40px 55px}h1{color:#126c65;font-size:28px}
section{padding-bottom:32px;margin-bottom:32px;border-bottom:1px solid #c8dedc}table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}
th,td{padding:10px;text-align:left;border-bottom:1px solid #dce5e8}th{background:#dcefed}tr:nth-child(even){background:#f4f7f9}
figure{margin:20px auto;text-align:center}img{width:100%;max-width:850px}figcaption{font-size:13px;color:#617781}
pre{background:#edf4f5;padding:20px;overflow:auto;font-size:13px}a{color:#126c65}@media print{body{background:white}main{padding:0}section{break-after:page}}'''
(ROOT / '课程参考报告.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
    '<title>Pump it Up 课程参考报告</title><style>' + css + '</style><main>' + ''.join(web) + '</main></html>', encoding='utf-8')
print(pdf_path)
