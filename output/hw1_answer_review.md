# HW1 答案检查与补图说明

检查对象：`hw1.pdf`（6 页）

## 总结

- 数值题整体正确：第 3(a)、3(c)、3(d)、4(a)、4(b) 的结果均可成立。
- 明确需要修改：第 1(a) 星形模式图中的 `data_dim` 应改为 `date_dim`。
- 建议完善：第 2 题应明确事实表粒度，并修正部分不严格的概念层次。
- 已补图：第 3(b) 箱线图、第 3(e) 散点图。

## 逐题检查

### 1(a) 星形模式

**结论：结构正确，但有一处拼写错误。**

- 中央事实表 `fact_sales` 与四个维表的星形结构正确。
- 图中的 `data_dim` 应改为 **`date_dim`**。
- 事实表列出的四个外键及两个度量正确。
- 如老师要求完整 schema，可在维表中补充示例属性，例如：
  - `date_dim(date_key, day, month, quarter, year)`
  - `product_dim(product_key, product_name, brand, category)`
  - `vendor_dim(vendor_key, vendor_name, vendor_city, vendor_country)`
  - `location_dim(location_key, city, state, country, region)`

### 1(b) OLAP 操作

**结论：正确。**

等价表达为：选择 `location = 'Los Angeles'`，将 `date` 上卷到 `year`，将 `product` 上卷到 `ALL`，保留 `vendor` 层次，并按 `(year, vendor)` 汇总 `SUM(sales_volume)`。

注意：题目原文及答案中出现了 `Los Angles`，标准拼写是 **Los Angeles**。实际查询时应以仓库中保存的成员值为准。

### 1(c) 位图索引

**结论：正确。**

你列出的低基数列、布尔组合、压缩、OLAP 查询、计数优势，以及高基数、更新成本、并发和维护问题都符合位图索引的特点。可再强调：位图索引最适合“读多写少”的数据仓库维属性。

### 2 区域气象局数据仓库

**结论：基本框架正确，但建议修改后提交。**

正确部分：

- 采用星形模式合理。
- `Time_Dim`、`Probe_Dim`、`Location_Dim` 三个维度及气压、温度、降水量三个观测指标合理。
- `probe -> station -> network` 和 `hour -> day -> month -> quarter -> year` 可作为概念层次。

建议修改：

1. 明确事实表粒度：**每个 probe 在每个整点的一条观测记录**。
2. 若每个 probe 固定安装在一个 location，`location_id` 可作为 `Probe_Dim` 的属性；若探针可移动或需要保留位置历史，则在事实表保留 `location_id` 是合理的，但应说明原因。
3. `probe -> probe_type -> manufacturer` 通常不是严格层次。更合适的是：
   - `probe -> model -> manufacturer`
   - `probe -> probe_type`（另一个独立分析路径）
4. `location -> city_or_region -> region -> climate_zone -> country` 不严格，因为 climate zone 与 country 往往是交叉分类，不是单一父子层次。建议改为：
   - `location -> city/sea_area -> region -> country`
   - `location -> climate_zone`
   - `location -> land_ocean`
5. 温度与气压不宜跨时间直接求和。为 OLAP 可增加 `observation_count`，并保存或派生 `min/max/avg temperature`、`min/max/avg pressure`；降水量可按时间求和。

一个更严谨的事实表描述为：

```text
Weather_Fact(
  time_key, probe_key, location_key,
  air_pressure, temperature, precipitation,
  observation_count, quality_flag
)
grain: one hourly observation per probe
```

### 3(a) 均值、中位数、标准差

**结论：正确。**

- 均值：`21.5`
- 中位数：`21.5`
- 总体标准差：`3.2171`，四舍五入为 `3.22`
- 样本标准差：`3.3007`，四舍五入为 `3.30`

若题目没有说明总体还是样本标准差，同时列出二者是稳妥的。

### 3(b) 箱线图

已绘制 `hw1_3b_boxplot_product_A.png`。

按“上下半组中位数”的 Tukey 规则：

- 最小值：`16`
- Q1：`19.5`
- 中位数：`21.5`
- Q3：`24`
- 最大值：`27`
- IQR：`4.5`
- 异常值界限：`12.75` 与 `30.75`，因此无异常值。

说明：某些软件采用线性插值，会给出 `Q1 = 19.75`；本图使用常见的手工箱线图规则 `Q1 = 19.5`。如课程指定了四分位数算法，应以课程规则为准。

### 3(c) Min-max 归一化

**结论：正确。**

使用公式 `(x - 16) / (27 - 16)`，你给出的 20 个归一化结果均正确（保留 4 位小数）。

### 3(d) Pearson 相关系数

**结论：正确。**

精确计算为 `r = 0.8308627`，四舍五入为 `0.831`。因此 A、B 销售量呈较强正相关。应避免把相关性表述成因果关系。

### 3(e) 散点图

已绘制 `hw1_3e_scatter_A_vs_B.png`。横轴为商品 A，纵轴为商品 B；点旁数字表示月份 1-20，并附线性拟合线及 `r = 0.831`。

### 4(a) Equal-depth binning：bin median

**结论：正确。**

排序后每箱 5 个数，共 4 箱；各箱中位数依次为 `17, 20, 23, 26`，平滑结果正确。

### 4(b) Equal-depth binning：bin boundaries

**结论：正确，但应说明平局规则。**

你的边界平滑结果正确。第 3 箱中的数值 `23` 到边界 `22` 和 `24` 距离相同；你采用“距离相同取较小边界”的规则，因此两个 `23` 都映射为 `22`。若老师规定平局取较大边界，则它们会映射为 `24`；最好在答案中补一句平局规则。

## 提交前建议修改清单

1. 将第 1(a) 图中的 `data_dim` 改成 `date_dim`。
2. 按上述建议调整第 2 题的概念层次，并补一句事实表粒度。
3. 插入第 3(b) 箱线图和第 3(e) 散点图。
4. 在第 4(b) 补充：边界距离相同时取较小边界。

