# 统计格式更新说明文档

## 1. 更新背景

根据业务需求，系统需要支持**按反馈聚合的多实体类型统计**，即一个反馈中识别到的多个实体类型和实体值需要作为一个组合进行统计，而不是之前的按单个实体类型统计。

## 2. 新格式说明

### 2.1 统计结果格式

**修改前（按实体类型单独统计）：**
```json
[
  {
    "entity_type": "业务类型",
    "entity_value": "报障",
    "feedback_count": 120,
    "ratio": 0.6
  },
  {
    "entity_type": "产品大类", 
    "entity_value": "净水设备",
    "feedback_count": 80,
    "ratio": 0.4
  }
]
```

**修改后（按反馈聚合的多实体组合统计）：**
```json
[
  {
    "entities": [
      {"entity_type": "业务类型", "entity_value": "建议"},
      {"entity_type": "产品大类", "entity_value": "净水设备"},
      {"entity_type": "具体产品", "entity_value": "益之源净水器"},
      {"entity_type": "问题现象", "entity_value": "噪音大"}
    ],
    "feedback_count": 35,
    "ratio": 0.175
  }
]
```

### 2.2 格式特点

1. **按反馈聚合**：每个统计项代表具有相同实体组合的反馈集合
2. **多实体类型**：一个统计项包含多个实体类型和对应的值
3. **完整语义**：保留了反馈的完整语义信息，实体之间的关联关系清晰
4. **统计准确**：`feedback_count` 表示具有该实体组合的反馈数量
5. **占比合理**：`ratio` 基于总反馈数计算，反映该组合在整体中的占比

## 3. 技术实现变更

### 3.1 核心SQL变更

**修改前的SQL（按实体类型分组）：**
```sql
SELECT 
    t.type_name AS entity_type,
    e.entity_value,
    COUNT(f.feedback_id) AS feedback_count
FROM 
    feedback_entity_relation f
JOIN 
    entity_vector_lib e ON f.entity_id = e.entity_id
JOIN 
    dynamic_entity_type t ON e.type_id = t.type_id
JOIN 
    customer_feedback c ON f.feedback_id = c.feedback_id
WHERE 
    DATE(c.create_time) = '{stat_date}'
GROUP BY 
    t.type_name, e.entity_value
ORDER BY 
    feedback_count DESC
```

**修改后的SQL（按反馈ID分组）：**
```sql
SELECT 
    f.feedback_id,
    MAX(c.feedback_text) AS feedback_text,
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'entity_type', t.type_name,
            'entity_value', e.entity_value
        )
    ) AS entity_combinations
FROM 
    feedback_entity_relation f
JOIN 
    entity_vector_lib e ON f.entity_id = e.entity_id
JOIN 
    dynamic_entity_type t ON e.type_id = t.type_id
JOIN 
    customer_feedback c ON f.feedback_id = c.feedback_id
WHERE 
    DATE(c.create_time) = '{stat_date}'
GROUP BY 
    f.feedback_id
```

### 3.2 数据处理逻辑变更

1. **实体组合解析**：
   - 解析JSON格式的实体组合
   - 创建实体类型到值的映射关系

2. **组合去重统计**：
   - 按实体组合进行去重
   - 统计每个组合出现的次数

3. **结果格式转换**：
   - 转换为要求的输出格式
   - 计算占比并排序

## 4. 对Coze智能体的影响

### 4.1 输入格式变更

**修改前的Coze输入：**
```json
{
  "stat_date": "2024-01-15",
  "stat_data": [
    {"entity_type": "业务类型", "entity_value": "报障", "feedback_count": 120, "ratio": 0.6},
    {"entity_type": "产品大类", "entity_value": "净水设备", "feedback_count": 80, "ratio": 0.4}
  ]
}
```

**修改后的Coze输入：**
```json
{
  "stat_date": "2024-01-15",
  "stat_data": [
    {
      "entities": [
        {"entity_type": "业务类型", "entity_value": "建议"},
        {"entity_type": "产品大类", "entity_value": "净水设备"},
        {"entity_type": "具体产品", "entity_value": "益之源净水器"},
        {"entity_type": "问题现象", "entity_value": "噪音大"}
      ],
      "feedback_count": 35,
      "ratio": 0.175
    }
  ]
}
```

### 4.2 Coze Prompt调整建议

为了适配新的输入格式，建议调整Coze智能体的分析Prompt：

```markdown
# 角色：客服反馈数据分析专家

## 核心指令
你需要基于客服反馈的统计数据，生成专业的分析总结报告，提供有价值的业务洞察。

## 输入数据说明
输入包含以下字段：
- `stat_date`: 统计日期
- `stat_data`: 统计数据数组，每个元素包含：
  - `entities`: 实体组合数组，每个实体包含 `entity_type` 和 `entity_value`
  - `feedback_count`: 具有该实体组合的反馈数量
  - `ratio`: 占比

## 分析维度
1. **实体组合分析**：
   - 识别高频实体组合模式
   - 分析不同实体类型之间的关联关系
   - 发现业务问题的典型特征组合

2. **问题聚焦分析**：
   - 基于完整实体组合识别问题场景
   - 分析问题现象与产品、业务类型的关联
   - 识别需要重点关注的问题组合

3. **业务洞察**：
   - 基于多维度实体组合提供更精准的洞察
   - 发现产品改进和服务优化的机会
   - 预测潜在的业务风险

## 输出格式要求
保持原有的输出格式不变，但在分析内容中体现多实体组合的价值。
```

## 5. 测试验证

### 5.1 测试脚本

提供了专门的测试脚本 `test_statistics.py` 用于验证新的统计逻辑：

```bash
# 运行测试脚本
cd /home/user/vibecoding/workspace/feedback-tagging-system/scripts
python test_statistics.py
```

### 5.2 验证要点

1. **格式正确性**：输出格式是否符合要求
2. **数据准确性**：统计数量和占比是否正确
3. **性能影响**：新逻辑对系统性能的影响
4. **Coze兼容性**：生成的数据是否能被Coze智能体正确处理

## 6. 部署建议

### 6.1 部署步骤

1. **备份原有脚本**：
   ```bash
   cp auto_analysis.py auto_analysis.py.bak
   ```

2. **部署新脚本**：
   直接替换 `auto_analysis.py` 文件

3. **运行测试**：
   ```bash
   python test_statistics.py
   ```

4. **监控运行**：
   ```bash
   tail -f logs/analysis.log
   ```

### 6.2 回滚方案

如果发现问题，可快速回滚到原版本：
```bash
cp auto_analysis.py.bak auto_analysis.py
```

## 7. 后续优化方向

1. **性能优化**：
   - 优化SQL查询性能
   - 考虑缓存机制减少重复计算

2. **功能扩展**：
   - 支持更复杂的实体组合分析
   - 提供自定义统计维度的能力

3. **可视化支持**：
   - 为多实体组合统计提供可视化展示
   - 支持交互式数据分析

## 8. 联系方式

如有任何问题或需要技术支持，请联系：
- 技术负责人：[您的姓名]
- 联系邮箱：[您的邮箱]
- 联系电话：[您的电话]