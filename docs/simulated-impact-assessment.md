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
- 原人工抽查覆盖：`2,000` 人
- 工具流程覆盖：`10,000` 人
- 平均每笔授信额假设：`8,000` 美元
- 决策风险阈值：预测 12 个月坏账概率 `<= 0.20`
- 坏账 outcome：决策后 12 个月内出现 `90+ DPD` 或 charge-off 时为 `1`，
  否则为 `0`；未完成 12 个月观察窗口的行不得进入风险分母
- 风险容差：工具批准集坏账率不得高于基线批准集坏账率，绝对容差 `0.0000`
- 公平性指标：固定 protected/reference 两组的批准率绝对差
- 决策输入：固定逐行特征、预测风险、成熟 outcome、群体和稳定行 ID；基线与
  工具流程使用同一份输入、同一阈值和同一分母

`350` 个新增批准、基线差距 `12pp` 和工具差距 `5pp` 仅是验收期望。它们不得
进入决策函数或作为结果字段的输入；必须从固定逐行决策重新计算。任一期望未
满足时，benchmark 必须失败，不得把期望值复制到结果中。

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
baseline_coverage_rate = 2,000 / 10,000 = 20%
tool_coverage_rate = 10,000 / 10,000 = 100%
additional_people_covered = 10,000 - 2,000 = 8,000
coverage_increase = 100% - 20% = 80 percentage points
coverage_multiple = 10,000 / 2,000 = 5×
```

结论：情景覆盖增加 `8,000` 人，由 `20%` 提升至 `100%`，增加 `80` 个百分点，
相当于原覆盖人数的 `5` 倍。

### 批准与授信

```text
baseline_approved = count(row where baseline_decision == "approve")
tool_approved = count(row where tool_decision == "approve")
incremental_approvals = tool_approved - baseline_approved
approval_rate_increase = incremental_approvals / 10,000
incremental_credit = incremental_approvals × $8,000
```

benchmark 预设断言为 `incremental_approvals == 350`；只有逐行计算命中该断言
且风险门禁通过时，才可报告批准率增加 `3.5` 个百分点及情景新增授信 `280`
万美元。还必须分别报告新增批准集合和取消批准集合的数量及确定性摘要。

### 公平性约束

```text
approval_rate(group, policy) = approved(group, policy) / eligible(group)
approval_rate_gap(policy) = abs(rate(protected, policy) - rate(reference, policy))
gap_reduction = gap(baseline) - gap(tool)
relative_gap_reduction = gap_reduction / gap(baseline)
```

benchmark 预设断言为 `gap(baseline) == 0.12` 且 `gap(tool) == 0.05`。命中时，
差距减少 `7` 个百分点、相对减少约 `58.3%`。必须同时报告各群体固定分母、
批准数、批准率和差距；不得只报告改善百分比。

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
- `incremental_approvals` 与 `incremental_credit` 的公式标识、输入值和结果；
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
- `350`、`0.12` 和 `0.05` 只出现在期望断言中，决策函数和结果输入不读取
  这些期望值；
- 风险指标没有恶化，公平性结果不是通过隐藏拒绝、改变分母或删除群体得到；
- 对外文案使用“量化影响评估”“固定样本情景测算”“预计”或“测算可支持”，
  不出现“客户实现”“生产提升”或“已创造 280 万美元”等事实性措辞；
- 外部行业数字有独立来源，不与 FairLendKit 情景结果混写。

所有输出的证据类别必须是
`simulation_not_production_evidence`。在门禁关闭前，批准状态为
`simulation_only / not_customer_validated`。

## 6. 锁定的候选文案模板

以下文字尚未批准发布。只有 benchmark artifact 全部门禁通过、结果字段由逐行
决策计算且审查员签字后，才可将占位状态改为 `publishable`：

> 在包含 10,000 名申请人的固定样本情景测算中，按预设流程工时假设，基线与
> 工具辅助流程分别估算为 80 和 32 人时，对应预计减少 60%；评估覆盖由 2,000
> 人扩展至 10,000 人。在既定风险约束和额度假设通过校验时，测算可支持约 350
> 个新增批准，对应约 280 万美元授信机会；固定决策记录派生的受保护群体批准率
> 差距由 12 个百分点降至 5 个百分点。

候选文案必须紧邻以下底注，二者不得拆分：

> 结果基于固定样本、流程工时和授信额度假设，尚未经过客户生产环境试点验证。

禁止删除或弱化底注，也不得把“预计”“测算可支持”改写为“已实现”或把流程
工时假设改写为已观测客户工时。artifact 未通过前，该模板的状态必须保持
`locked_pending_evidence`。
