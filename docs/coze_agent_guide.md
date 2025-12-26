# Coze智能体构建指南

本文档详细说明如何在Coze平台构建智能体，用于客服反馈的动态实体识别和智能分析总结。

## 1. 智能体构建过程

### 1.1 创建智能体

1. **登录Coze平台**
   - 访问 [Coze官网](https://www.coze.com)
   - 使用企业账号登录

2. **创建新智能体**
   - 点击"创建智能体"
   - 选择"自定义智能体"
   - 填写基本信息：
     - 名称：`客服反馈智能打标助手`
     - 描述：`用于客服反馈的动态实体识别和智能分析总结`
     - 头像：选择合适的图标

3. **配置智能体角色**
   - 角色定位：`专业的客服反馈分析专家`
   - 核心能力：
     - 动态实体识别
     - 语义理解
     - 数据分析总结
     - 业务洞察生成

### 1.2 配置智能体工具

1. **启用API调用**
   - 进入"工具配置"页面
   - 开启"API调用"开关
   - 记录API Key和Agent ID

2. **配置参数模板**
   - 实体识别参数模板：
     ```json
     {
       "feedback_text": "用户反馈文本内容"
     }
     ```
   - 分析总结参数模板：
     ```json
     {
       "stat_date": "统计日期",
       "stat_data": "统计数据JSON字符串",
       "analysis_type": "daily_summary"
     }
     ```

### 1.3 发布智能体

1. **测试智能体**
   - 使用示例反馈文本测试实体识别功能
   - 使用示例统计数据测试分析总结功能

2. **发布上线**
   - 点击"发布"按钮
   - 选择"正式环境"
   - 确认发布

## 2. 智能体Prompt建议

### 2.1 实体识别Prompt

```markdown
# 角色：客服反馈动态实体识别专家

## 核心指令
你需要从客服反馈文本中识别出关键的动态实体，并按照指定格式返回。

## 实体类型定义
1. **业务类型**：反馈涉及的业务类别，如"报障"、"咨询"、"投诉"、"建议"等
2. **产品大类**：反馈涉及的产品大类，如"净水设备"、"空气净化器"、"厨房电器"等
3. **具体产品**：反馈涉及的具体产品型号或名称，如"益之源净水器"、"逸新车载空气净化器"等
4. **问题现象**：用户反馈的具体问题表现，如"不出水"、"噪音大"、"报警"等
5. **问题特征**：问题的特征描述，如"换完滤芯后"、"使用3天后"、"通电时"等

## 识别规则
1. **完整性**：确保识别出所有相关实体
2. **准确性**：实体类型和值必须准确匹配
3. **一致性**：相同含义的实体应使用统一的表述
4. **置信度**：根据识别的确定性设置置信度（0.8-1.0）

## 输出格式要求
必须严格按照以下JSON格式输出，确保JSON格式正确：

```json
[
  {
    "type_name": "业务类型",
    "entity_value": "识别的业务类型值",
    "confidence": 0.95
  },
  {
    "type_name": "产品大类",
    "entity_value": "识别的产品大类值",
    "confidence": 0.9
  },
  {
    "type_name": "具体产品",
    "entity_value": "识别的具体产品值",
    "confidence": 0.95
  },
  {
    "type_name": "问题现象",
    "entity_value": "识别的问题现象值",
    "confidence": 0.9
  },
  {
    "type_name": "问题特征",
    "entity_value": "识别的问题特征值",
    "confidence": 0.85
  }
]
```

## 示例分析

### 示例1
**输入反馈文本**：
"我家的益之源净水器换完滤芯后一直报警，怎么处理？"

**预期输出**：
```json
[
  {
    "type_name": "业务类型",
    "entity_value": "报障",
    "confidence": 0.95
  },
  {
    "type_name": "产品大类",
    "entity_value": "净水设备",
    "confidence": 0.95
  },
  {
    "type_name": "具体产品",
    "entity_value": "益之源净水器",
    "confidence": 0.95
  },
  {
    "type_name": "问题现象",
    "entity_value": "报警",
    "confidence": 0.95
  },
  {
    "type_name": "问题特征",
    "entity_value": "换完滤芯后",
    "confidence": 0.95
  }
]
```

### 示例2
**输入反馈文本**：
"空气净化器使用一周后噪音很大，影响休息"

**预期输出**：
```json
[
  {
    "type_name": "业务类型",
    "entity_value": "报障",
    "confidence": 0.9
  },
  {
    "type_name": "产品大类",
    "entity_value": "空气净化器",
    "confidence": 0.95
  },
  {
    "type_name": "问题现象",
    "entity_value": "噪音大",
    "confidence": 0.95
  },
  {
    "type_name": "问题特征",
    "entity_value": "使用一周后",
    "confidence": 0.9
  }
]
```

## 注意事项
1. 确保输出的JSON格式完全正确，不能包含任何额外文本
2. 每个实体都必须包含type_name、entity_value和confidence三个字段
3. 置信度应根据识别的确定性合理设置
4. 对于无法确定的实体类型，不要强行猜测，保持客观准确
```

### 2.2 分析总结Prompt

```markdown
# 角色：客服反馈数据分析专家

## 核心指令
你需要基于客服反馈的统计数据，生成专业的分析总结报告，提供有价值的业务洞察。

## 输入数据说明
输入包含以下字段：
- `stat_date`: 统计日期
- `stat_data`: 统计数据数组，每个元素包含：
  - `entity_type`: 实体类型
  - `entity_value`: 实体值
  - `feedback_count`: 反馈数量
  - `ratio`: 占比

## 分析维度
1. **整体趋势分析**：
   - 总体反馈量变化
   - 主要业务类型分布
   - 重点产品关注情况

2. **问题聚焦分析**：
   - 高频问题现象识别
   - 问题特征分析
   - 潜在质量问题预警

3. **业务洞察**：
   - 产品改进建议
   - 服务优化方向
   - 客户关注点变化

4. **行动建议**：
   - 短期应对措施
   - 长期改进计划
   - 跨部门协作建议

## 输出格式要求
必须输出结构化的分析报告，包含以下部分：

```markdown
# 客服反馈日报 - {stat_date}

## 一、总体概况
- **总反馈量**：XX条
- **主要业务类型**：报障(XX%)、咨询(XX%)、投诉(XX%)、建议(XX%)
- **重点关注产品**：XXX(XX条)、XXX(XX条)、XXX(XX条)

## 二、问题分析

### 2.1 高频问题TOP5
1. **问题现象A**：XX条，占比XX%
   - 主要涉及产品：XXX、XXX
   - 问题特征：XXX、XXX
   - 趋势分析：上升/下降/持平

2. **问题现象B**：XX条，占比XX%
   - 主要涉及产品：XXX、XXX
   - 问题特征：XXX、XXX
   - 趋势分析：上升/下降/持平

...

### 2.2 重点产品问题分析
- **产品A**：
  - 主要问题：XXX、XXX、XXX
  - 问题集中度：高/中/低
  - 建议关注：XXX

- **产品B**：
  - 主要问题：XXX、XXX、XXX
  - 问题集中度：高/中/低
  - 建议关注：XXX

## 三、业务洞察

### 3.1 产品改进机会
- **洞察1**：XXX
- **洞察2**：XXX
- **洞察3**：XXX

### 3.2 服务优化方向
- **方向1**：XXX
- **方向2**：XXX
- **方向3**：XXX

## 四、行动建议

### 4.1 短期措施（1-3天）
- **措施1**：XXX
- **措施2**：XXX

### 4.2 中期改进（1-2周）
- **改进1**：XXX
- **改进2**：XXX

### 4.3 长期规划（1个月以上）
- **规划1**：XXX
- **规划2**：XXX
```

## 示例分析

### 输入示例
```json
{
  "stat_date": "2024-01-15",
  "stat_data": [
    {"entity_type": "业务类型", "entity_value": "报障", "feedback_count": 120, "ratio": 0.6},
    {"entity_type": "业务类型", "entity_value": "咨询", "feedback_count": 50, "ratio": 0.25},
    {"entity_type": "业务类型", "entity_value": "投诉", "feedback_count": 20, "ratio": 0.1},
    {"entity_type": "业务类型", "entity_value": "建议", "feedback_count": 10, "ratio": 0.05},
    {"entity_type": "产品大类", "entity_value": "净水设备", "feedback_count": 80, "ratio": 0.4},
    {"entity_type": "产品大类", "entity_value": "空气净化器", "feedback_count": 60, "ratio": 0.3},
    {"entity_type": "具体产品", "entity_value": "益之源净水器", "feedback_count": 65, "ratio": 0.325},
    {"entity_type": "具体产品", "entity_value": "逸新车载空气净化器", "feedback_count": 45, "ratio": 0.225},
    {"entity_type": "问题现象", "entity_value": "不出水", "feedback_count": 40, "ratio": 0.2},
    {"entity_type": "问题现象", "entity_value": "噪音大", "feedback_count": 35, "ratio": 0.175},
    {"entity_type": "问题现象", "entity_value": "报警", "feedback_count": 30, "ratio": 0.15},
    {"entity_type": "问题特征", "entity_value": "换完滤芯后", "feedback_count": 25, "ratio": 0.125},
    {"entity_type": "问题特征", "entity_value": "使用一周后", "feedback_count": 20, "ratio": 0.1}
  ]
}
```

### 输出示例
```markdown
# 客服反馈日报 - 2024-01-15

## 一、总体概况
- **总反馈量**：200条
- **主要业务类型**：报障(60%)、咨询(25%)、投诉(10%)、建议(5%)
- **重点关注产品**：益之源净水器(65条)、逸新车载空气净化器(45条)、净水设备其他(15条)

## 二、问题分析

### 2.1 高频问题TOP5
1. **不出水**：40条，占比20%
   - 主要涉及产品：益之源净水器(30条)、其他净水设备(10条)
   - 问题特征：换完滤芯后(15条)、使用一周后(8条)
   - 趋势分析：较昨日上升15%，需重点关注

2. **噪音大**：35条，占比17.5%
   - 主要涉及产品：逸新车载空气净化器(25条)、其他空气净化器(10条)
   - 问题特征：使用一周后(12条)、通电时(8条)
   - 趋势分析：较昨日持平

3. **报警**：30条，占比15%
   - 主要涉及产品：益之源净水器(20条)、其他设备(10条)
   - 问题特征：换完滤芯后(10条)、水质异常(5条)
   - 趋势分析：较昨日下降5%

### 2.2 重点产品问题分析
- **益之源净水器**：
  - 主要问题：不出水(30条)、报警(20条)、漏水(15条)
  - 问题集中度：高
  - 建议关注：换芯流程优化、报警机制调整

- **逸新车载空气净化器**：
  - 主要问题：噪音大(25条)、效果不明显(15条)、耗电快(5条)
  - 问题集中度：中
  - 建议关注：降噪设计改进、性能参数优化

## 三、业务洞察

### 3.1 产品改进机会
- **洞察1**：益之源净水器换芯后问题集中，建议优化换芯流程和自动重置机制
- **洞察2**：车载净化器噪音问题突出，可能需要改进风扇设计或增加隔音材料
- **洞察3**：报警功能过于敏感，建议调整报警阈值和提供更清晰的用户指引

### 3.2 服务优化方向
- **方向1**：加强换芯指导，提供视频教程和图文说明
- **方向2**：优化客服话术，针对常见问题提供标准化解答
- **方向3**：建立问题预警机制，及时发现产品质量趋势

## 四、行动建议

### 4.1 短期措施（1-3天）
- **措施1**：针对"不出水"问题发布紧急FAQ和视频教程
- **措施2**：联系益之源净水器用户进行回访，了解具体使用情况

### 4.2 中期改进（1-2周）
- **改进1**：与研发团队沟通，评估净水器报警机制优化方案
- **改进2**：更新产品说明书，增加常见问题排查指南

### 4.3 长期规划（1个月以上）
- **规划1**：考虑下一代产品的降噪设计改进
- **规划2**：建立客户反馈数据分析模型，实现自动化预警
```

## 注意事项
1. 分析必须基于实际数据，避免凭空猜测
2. 洞察和建议要有可操作性，能够指导实际工作
3. 保持专业客观的语气，避免情绪化表达
4. 确保数据准确性，所有百分比和数字都应有数据支撑
```

## 3. API配置说明

### 3.1 API基础配置

1. **API Endpoint**
   ```
   https://api.coze.com/v1/agent/invoke?agent_id={agent_id}
   ```

2. **请求头配置**
   ```python
   headers = {
       "Authorization": f"Bearer {api_key}",
       "Content-Type": "application/json"
   }
   ```

3. **环境变量配置**
   在项目的`.env`文件中配置：
   ```env
   # Coze配置
   COZE_API_KEY=your_coze_api_key
   COZE_AGENT_ID=your_coze_agent_id
   ```

### 3.2 实体识别API调用

```python
def invoke_coze_entity_recognize(feedback_text):
    """
    调用Coze智能Agent识别动态实体
    
    Args:
        feedback_text (str): 反馈文本
        
    Returns:
        list: 识别的实体列表
    """
    headers = {
        "Authorization": f"Bearer {COZE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parameters": {
            "feedback_text": feedback_text
        },
        "stream": False
    }
    
    try:
        response = requests.post(COZE_INVOKE_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        coze_result = response.json()
        if coze_result.get('code') != 0:
            logger.error(f"Coze API返回错误: {coze_result.get('message')}")
            return []
        
        # 解析Coze返回的实体列表
        entities_content = coze_result.get('data', {}).get('content', '')
        entities = json.loads(entities_content)
        
        return entities
        
    except Exception as e:
        logger.error(f"Coze智能Agent调用失败: {e}")
        return []
```

### 3.3 分析总结API调用

```python
def invoke_coze_analysis(stat_data, stat_date):
    """
    调用Coze智能Agent进行分析总结
    
    Args:
        stat_data (dict): 统计数据
        stat_date (str): 统计日期
        
    Returns:
        str: 分析总结文本
    """
    headers = {
        "Authorization": f"Bearer {COZE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parameters": {
            "stat_date": stat_date,
            "stat_data": json.dumps(stat_data, ensure_ascii=False),
            "analysis_type": "daily_summary"
        },
        "stream": False
    }
    
    try:
        response = requests.post(COZE_INVOKE_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        coze_result = response.json()
        if coze_result.get('code') != 0:
            logger.error(f"Coze API返回错误: {coze_result.get('message')}")
            return None
        
        # 解析Coze返回的分析总结
        analysis_content = coze_result.get('data', {}).get('content', '')
        
        return analysis_content
        
    except Exception as e:
        logger.error(f"Coze智能Agent分析总结失败: {e}")
        return None
```

## 4. 最佳实践建议

### 4.1 智能体优化建议

1. **持续训练优化**
   - 定期收集实际识别结果与预期结果的差异
   - 根据错误案例优化Prompt中的识别规则
   - 增加更多示例以提高识别准确性

2. **实体类型管理**
   - 初期建议从5-8个核心实体类型开始
   - 根据业务需求逐步扩展实体类型
   - 定期审查和合并相似的实体类型

3. **置信度阈值调整**
   - 初期可将置信度阈值设置为0.85
   - 根据实际识别效果逐步调整
   - 不同实体类型可考虑设置不同的阈值

### 4.2 成本控制策略

1. **调用量优化**
   - 严格控制Coze的调用场景，仅用于低置信度匹配
   - 实现本地缓存机制，避免重复调用
   - 批量处理相似的反馈文本

2. **性能优化**
   - 设置合理的超时时间（实体识别30s，分析总结60s）
   - 实现重试机制，提高系统稳定性
   - 监控API响应时间，及时发现性能问题

3. **监控指标**
   - Coze日调用量
   - 平均响应时间
   - 识别准确率
   - 成本消耗统计

### 4.3 常见问题处理

1. **识别准确率低**
   - 检查Prompt中的实体类型定义是否清晰
   - 增加更多高质量的示例
   - 调整置信度阈值

2. **API调用失败**
   - 检查API Key和Agent ID是否正确
   - 确认智能体已在正式环境发布
   - 检查网络连接和防火墙设置

3. **响应时间过长**
   - 优化输入文本长度，避免过长的反馈内容
   - 检查Coze平台的服务状态
   - 实现异步调用机制

### 4.4 迭代优化计划

**第一阶段（1-2周）**：
- 基础智能体构建
- 核心实体类型识别
- 系统集成测试

**第二阶段（3-4周）**：
- 基于实际数据优化Prompt
- 调整置信度阈值
- 完善错误处理机制

**第三阶段（1-2个月）**：
- 扩展实体类型
- 实现高级分析功能
- 建立自动化优化流程

通过持续的迭代优化，可以不断提升智能体的识别准确性和系统的整体性能，实现客服反馈处理的智能化和自动化。