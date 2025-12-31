#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试统计功能的脚本
用于验证修改后的统计逻辑是否正确生成按反馈聚合的实体组合统计
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入需要测试的函数
from auto_analysis import generate_statistics, seekdb_client

def test_statistics_generation():
    """
    测试统计结果生成功能
    """
    logger.info("开始测试统计结果生成功能")
    
    # 使用昨天的日期进行测试
    test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    logger.info(f"测试日期: {test_date}")
    
    try:
        # 生成统计结果
        stat_df = generate_statistics(test_date)
        
        if stat_df.empty:
            logger.warning(f"测试日期 {test_date} 无数据，请检查数据库中是否有该日期的反馈数据")
            return
        
        logger.info(f"成功生成 {len(stat_df)} 条统计结果")
        
        # 打印前几条结果用于验证
        logger.info("前5条统计结果:")
        for i, row in stat_df.head().iterrows():
            logger.info(f"第{i+1}条:")
            logger.info(f"  实体组合: {json.dumps(row['entities'], ensure_ascii=False, indent=2)}")
            logger.info(f"  反馈数量: {row['feedback_count']}")
            logger.info(f"  占比: {row['ratio']:.4f}")
            logger.info("-" * 50)
        
        # 验证数据格式
        validate_statistics_format(stat_df)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def validate_statistics_format(stat_df):
    """
    验证统计结果的格式是否正确
    
    Args:
        stat_df (DataFrame): 统计结果DataFrame
    """
    logger.info("开始验证统计结果格式")
    
    required_columns = ['entities', 'feedback_count', 'ratio']
    for col in required_columns:
        if col not in stat_df.columns:
            logger.error(f"缺少必需的列: {col}")
            return False
    
    # 验证entities列的格式
    for i, row in stat_df.iterrows():
        entities = row['entities']
        if not isinstance(entities, list):
            logger.error(f"第{i+1}条记录的entities不是列表类型")
            return False
        
        for entity in entities:
            if not isinstance(entity, dict):
                logger.error(f"第{i+1}条记录的entity不是字典类型")
                return False
            
            required_entity_fields = ['entity_type', 'entity_value']
            for field in required_entity_fields:
                if field not in entity:
                    logger.error(f"第{i+1}条记录的entity缺少必需字段: {field}")
                    return False
    
    # 验证统计数值
    for i, row in stat_df.iterrows():
        if not isinstance(row['feedback_count'], int) or row['feedback_count'] < 0:
            logger.error(f"第{i+1}条记录的feedback_count无效: {row['feedback_count']}")
            return False
        
        if not isinstance(row['ratio'], float) or row['ratio'] < 0 or row['ratio'] > 1:
            logger.error(f"第{i+1}条记录的ratio无效: {row['ratio']}")
            return False
    
    logger.info("统计结果格式验证通过")
    return True


def test_coze_input_format():
    """
    测试生成的统计数据是否符合Coze智能体的输入格式
    """
    logger.info("开始测试Coze输入格式")
    
    test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        # 生成统计结果
        stat_df = generate_statistics(test_date)
        
        if stat_df.empty:
            logger.warning(f"测试日期 {test_date} 无数据，无法测试Coze输入格式")
            return
        
        # 转换为Coze输入格式
        stat_data = []
        for _, row in stat_df.iterrows():
            stat_item = {
                "entities": row['entities'],
                "feedback_count": row['feedback_count'],
                "ratio": row['ratio']
            }
            stat_data.append(stat_item)
        
        # 打印转换后的格式
        logger.info("转换后的Coze输入格式:")
        logger.info(json.dumps(stat_data[:3], ensure_ascii=False, indent=2))
        
        # 验证格式是否符合要求
        for i, item in enumerate(stat_data[:3]):
            logger.info(f"验证第{i+1}条数据:")
            logger.info(f"  格式: {json.dumps(item, ensure_ascii=False)}")
            
            # 检查是否包含所有必需字段
            required_fields = ['entities', 'feedback_count', 'ratio']
            for field in required_fields:
                if field not in item:
                    logger.error(f"  缺少必需字段: {field}")
                else:
                    logger.info(f"  ✓ 包含字段: {field}")
            
            # 检查entities格式
            if 'entities' in item:
                entities = item['entities']
                if isinstance(entities, list):
                    logger.info(f"  ✓ entities是列表类型，包含 {len(entities)} 个实体")
                    for entity in entities:
                        if isinstance(entity, dict) and 'entity_type' in entity and 'entity_value' in entity:
                            logger.info(f"    ✓ 实体: {entity['entity_type']}={entity['entity_value']}")
                        else:
                            logger.error(f"    ✗ 实体格式不正确: {entity}")
                else:
                    logger.error(f"  ✗ entities不是列表类型")
            
            logger.info("-" * 50)
        
    except Exception as e:
        logger.error(f"测试Coze输入格式时发生错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    主函数
    """
    logger.info("===== 统计功能测试开始 =====")
    
    # 测试统计结果生成
    test_statistics_generation()
    
    # 测试Coze输入格式
    test_coze_input_format()
    
    logger.info("===== 统计功能测试结束 =====")


if __name__ == "__main__":
    main()