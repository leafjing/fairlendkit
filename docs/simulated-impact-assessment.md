# FairLendKit 量化影响评估（固定样本情景测算）

> 状态：待 benchmark 产物回填。本文全部业务影响数字均为可复算的情景评估，
> 不是客户试点、生产部署、历史交易或已实现商业成效。

## 1. 三层证据必须分开

1. **行业量化结果**：只能引用可核验的外部来源，并保留作者、标题、年份、
   URL、适用场景和限制。行业结果不能归因于 FairLendKit。
2. **具体贡献**：可陈述已完成的数据源评估、隐私和标识符隔离、权重与插补
   校验、时间泄漏防护、可复现测试及 fail-closed 门禁。这些是可审计交付，
   但本身不等于客户业务成效。
3. **FairLendKit 情景结果**：只能基于本页固定输入和公式报告。机器可读
   evidence class 必须表明它不是生产证据。benchmark 未生成前，数字只是验收
   期望，不是已观测结果。

当前没有在本页批准任何无来源的“行业平均提升”数字。外部证据缺失时，应写
“行业量化证据待补”，不得用下述情景数字替代。

## 2. 固定情景

- 情景 ID：`fairlendkit-sim-impact-v1`
- 申请人数：`N = 10,000`
- 每个工作日：`8` 小时
- 原人工公平性复核：`2` 名分析师 × `5` 个工作日
- FairLendKit 辅助流程：`2` 名分析师 × `2` 个工作日
- 基线与工具覆盖人数：由同一输入上的实际决策记录派生
- 固定平均授信额：`$8,000`；仅用于本情景的授信机会测算
- 决策风险阈值：预测 12 个月坏账概率 `<= 0.20`
- 坏账 outcome：决策后 12 个月内出现 `90+ DPD` 或 charge-off 时为 `1`，
  否则为 `0`；未完成 12 个月观察窗口的行不得进入风险分母
- 风险容差：工具批准集坏账率不得高于基线批准集坏账率，绝对容差 `0.0000`
- 公平性指标：固定 protected/reference 两组的批准率绝对差
- 决策输入：固定逐行特征、预测风险、成熟 outcome、群体和稳定行
  ID；基线与工具流程使用同一份输入、同一阈值和同一分母

批准增量、覆盖人数、授信增量和公平性差距不得作为结果输入，必须从固定逐行
决策重新计算。若配置另设验收门槛，门槛必须与结果分字段记录、纳入配置哈希，
且不得被复制为结果。

## 3. 公式与可复算结果

### 后处理人时

```text
baseline_person_hours = 2 × 5 × 8 = 80
tool_assisted_person_hours = 2 × 2 × 8 = 32
person_hours_saved = 80 - 32 = 48
time_reduction_rate = 48 / 80 = 60%
```

结论：情景后处理与验证人时由 `80` 降至 `32`，减少 `48` 人时，即 `60%`。

### 覆盖人数

```text
baseline_coverage_rate = baseline_covered_count / eligible_count
tool_coverage_rate = tool_covered_count / eligible_count
additional_people_covered = tool_covered_count - baseline_covered_count
coverage_increase = tool_coverage_rate - baseline_coverage_rate
coverage_multiple = tool_covered_count / baseline_covered_count
```

所有覆盖数字由 artifact 注入；在“覆盖”的行级判定和分母通过复审前，不得发布
覆盖人数、覆盖率、增量或倍数。

### 批准与授信

```text
baseline_approved = count(row where baseline_decision == "approve")
tool_approved = count(row where tool_decision == "approve")
incremental_approvals = tool_approved - baseline_approved
approval_rate_increase = incremental_approvals / eligible_count
fixed_credit_amount_usd = 8000
credit_increase_usd = incremental_approvals * fixed_credit_amount_usd
```

只有逐行计算和风险门禁通过时，才可由 artifact 注入批准率变化及按固定平均
额度计算的授信机会。
还必须分别报告新增批准集合和取消批准集合的数量及确定性摘要。

### 公平性约束

```text
approval_rate(group, policy) = approved(group, policy) / eligible(group)
approval_rate_gap(policy) = abs(rate(protected, policy) - rate(reference, policy))
gap_reduction = gap(baseline) - gap(tool)
relative_gap_reduction = gap_reduction / gap(baseline)
```

必须同时报告各群体固定分母、批准数、批准率和差距；不得只报告改善百分比。
候选文案中的公平性数字只能从通过复审的 artifact 注入。

### 风险非劣效门禁

```text
matured_approved(policy) = approved rows whose 12-month outcome is observed
bad_rate(policy) = sum(y_bad for matured_approved(policy)) / count(matured_approved(policy))
risk_delta = bad_rate(tool) - bad_rate(baseline)
risk_gate_pass = risk_delta <= 0.0000
```

任一批准集的成熟 outcome 分母为零时，以 `impact_risk_denominator_empty` 失败；
风险恶化时以 `impact_risk_noninferiority_failed` 失败；输入含未定义 outcome、窗口
或阈值时以 `impact_outcome_contract_invalid` 失败。失败时不得发布批准或授信收益。

## 4. benchmark 必须产出的证据

程序化 benchmark 必须输出一个机器可读 artifact，至少包含：

- `scenario_id`、代码 commit、配置摘要、随机种子、运行环境和时间戳；
- `evidence_class=simulation_not_production_evidence`；
- 完整运行命令、输入文件 SHA-256、配置 SHA-256 和有序稳定行 ID 摘要；
- 基线与工具流程的 wall-clock 时间、重复次数、均值及离散程度；
- `baseline_person_hours=80` 与 `tool_assisted_person_hours=32`，并标注为情景
  人工投入假设，而非由 wall-clock 自动推导；
- 总申请人数、基线覆盖人数、工具覆盖人数及覆盖率；
- 基线与工具批准人数、批准率、净新增批准数，以及新增/取消批准集合各自的
  SHA-256 摘要；
- `incremental_approvals`、`fixed_credit_amount_usd=8000` 与
  `credit_increase_usd = incremental_approvals * fixed_credit_amount_usd` 的公式
  标识、输入值和结果；固定额度假设必须写入 artifact 配置并纳入配置
  SHA-256；
- outcome 定义、12 个月观察窗口、`0.20` 风险阈值、成熟分母、两组坏账率、
  `risk_delta`、`0.0000` 容差和 risk reason code；
- 各受保护群体样本量、批准率、批准率差距及不确定性；
- 数据来源身份、允许用途，以及是否为合成、公开 benchmark 或真实试用数据；
- 任一约束失败时的 fail-closed 状态和稳定 reason code。

工具运行时间与分析师人时是不同指标，禁止用一次脚本运行的秒数直接证明
“节省 48 人时”。人时数字只有在任务分解、人员数、工作日和重复执行记录均
被固定后才可作为情景估算报告。

## 5. 发布门禁

对外使用本页数字前必须同时满足：

- benchmark artifact 可由仓库 commit 和固定配置复算；
- 基线与工具流程使用完全相同的评估样本、标签、时间窗口、风险阈值、
  额度假设和群体定义；
- 审查员确认所有数字可由 artifact 或本页公式得到；
- 任何配置验收门槛与派生结果分字段记录，决策函数和结果输入不读取门槛值；
- 风险指标没有恶化，公平性结果不是通过隐藏拒绝、改变分母或删除群体得到；
- 对外文案使用“量化影响评估”“固定样本情景测算”“预计”或“测算可支持”，
  不出现“客户实现”“生产提升”或“已创造授信额”等事实性措辞；
- 外部行业数字有独立来源，不与 FairLendKit 情景结果混写。

所有输出的证据类别必须是
`simulation_not_production_evidence`。在门禁关闭前，批准状态为
`simulation_only / not_customer_validated`。

## 6. 锁定的候选文案模板

以下文字尚未批准发布。只有 benchmark artifact 全部门禁通过、结果字段由逐行
决策计算且审查员签字后，才可将占位状态改为 `publishable`：

> 在包含 `{eligible_count}` 名申请人的固定样本情景测算中，按预设人工流程工时
> 假设，基线与工具辅助流程分别估算为 80 和 32 人时，对应预计减少 60%；评估
> 覆盖由 `{baseline_covered_count}` 人扩展至 `{tool_covered_count}` 人。在既定
> 风险约束通过校验时，测算可支持 `{incremental_approvals}` 个净新增
> 批准，对应 `{credit_increase_usd}` 授信机会；固定决策记录派生的受保护群体
> 批准率差距由 `{baseline_approval_rate_gap}` 变为 `{tool_approval_rate_gap}`。

候选文案必须紧邻以下底注，二者不得拆分：

> 结果基于固定样本、预设人工流程工时和固定平均授信额度，尚未经过客户生产环境
> 试点验证。

禁止删除或弱化底注，也不得把“预计”“测算可支持”改写为“已实现”或把流程
工时假设改写为已观测客户工时。artifact 未通过前，该模板的状态必须保持
`locked_pending_evidence`。
