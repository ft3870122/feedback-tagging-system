#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
客服反馈分析总结脚本
对应架构图中的“分析总结”流程：
- 统计结果生成
- 智能Agent分析总结
- 结果存储
"""

import os
import sys
import json
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from seekdb_client import SeekDBClient

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/analysis.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------- 配置加载 ----------------------
# SeekDB配置
SEEKDB_CONFIG = {
    'host': os.getenv('SEEKDB_HOST', 'localhost'),
    'port': int(os.getenv('SEEKDB_PORT', 2881)),
    'user': os.getenv('SEEKDB_USER', 'root'),
    'password': os.getenv('SEEKDB_PASSWORD', ''),
    'database': os.getenv('SEEKDB_DATABASE', 'feedback_db')
}

# Coze配置
COZE_API_KEY = os.getenv('COZE_API_KEY', '')
COZE_AGENT_ID = os.getenv('COZE_AGENT_ID', '')
COZE_INVOKE_URL = f"https://api.coze.com/v1/agent/invoke?agent_id={COZE_AGENT_ID}"

# 系统配置
ANALYSIS_DATE = os.getenv('ANALYSIS_DATE', (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))

# ---------------------- SeekDB客户端初始化 ----------------------
try:
    seekdb_client = SeekDBClient(**SEEKDB_CONFIG)
    logger.info("SeekDB客户端初始化成功")
except Exception as e:
    logger.error(f"SeekDB客户端初始化失败: {e}")
    sys.exit(1)

# ---------------------- 核心函数 ----------------------

def generate_statistics(stat_date):
    """
    生成统计结果
    对应架构图中的“统计结果生成”
    
    Args:
        stat_date (str): 统计日期
        
    Returns:
        DataFrame: 统计结果
    """
    try:
        # 统计SQL：按反馈聚合，获取每个反馈的实体组合
        stat_sql = f"""
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
        """
        
        stat_result = seekdb_client.query_sql(stat_sql)
        
        if stat_result.empty:
            logger.info(f"日期 {stat_date} 无反馈数据")
            return pd.DataFrame()
        
        # 处理实体组合，生成按实体类型聚合的统计
        entity_statistics = []
        total_feedbacks = len(stat_result)
        
        for _, row in stat_result.iterrows():
            try:
                # 解析实体组合JSON
                entity_combinations = json.loads(row['entity_combinations'])
                
                # 创建实体类型到值的映射
                entity_map = {}
                for entity in entity_combinations:
                    entity_type = entity.get('entity_type')
                    entity_value = entity.get('entity_value')
                    if entity_type and entity_value:
                        entity_map[entity_type] = entity_value
                
                # 添加到统计列表
                if entity_map:
                    entity_statistics.append({
                        'feedback_id': row['feedback_id'],
                        'feedback_text': row['feedback_text'],
                        'entity_map': entity_map
                    })
            except Exception as e:
                logger.warning(f"解析反馈 {row['feedback_id']} 的实体组合失败: {e}")
                continue
        
        if not entity_statistics:
            logger.info(f"日期 {stat_date} 无有效实体组合数据")
            return pd.DataFrame()
        
        # 按实体类型和值的组合进行统计
        combination_counts = {}
        for item in entity_statistics:
            entity_map = item['entity_map']
            # 将实体映射转换为可哈希的格式
            combination_key = str(sorted(entity_map.items()))
            if combination_key not in combination_counts:
                combination_counts[combination_key] = {
                    'count': 0,
                    'entity_map': entity_map
                }
            combination_counts[combination_key]['count'] += 1
        
        # 生成最终统计结果
        final_statistics = []
        for combo_info in combination_counts.values():
            # 创建符合要求格式的统计项
            stat_item = {
                'entities': []
            }
            
            # 添加所有实体类型和值
            for entity_type, entity_value in combo_info['entity_map'].items():
                stat_item['entities'].append({
                    'entity_type': entity_type,
                    'entity_value': entity_value
                })
            
            # 添加统计信息
            stat_item['feedback_count'] = combo_info['count']
            stat_item['ratio'] = round(combo_info['count'] / total_feedbacks, 4)
            
            final_statistics.append(stat_item)
        
        # 转换为DataFrame并排序
        result_df = pd.DataFrame(final_statistics)
        result_df = result_df.sort_values('feedback_count', ascending=False)
        
        logger.info(f"成功生成 {len(result_df)} 条统计结果")
        return result_df
        
    except Exception as e:
        logger.error(f"生成统计结果失败: {e}")
        return pd.DataFrame()


def store_statistics(stat_df, stat_date):
    """
    存储统计结果
    对应架构图中的“统计结果”存储
    
    Args:
        stat_df (DataFrame): 统计结果
        stat_date (str): 统计日期
    """
    try:
        # 先删除当天已有的统计结果
        delete_sql = f"DELETE FROM feedback_stat WHERE stat_date = '{stat_date}'"
        seekdb_client.execute_sql(delete_sql)
        
        # 批量插入新的统计结果
        inserted_count = 0
        for _, row in stat_df.iterrows():
            # 遍历每个实体组合中的实体
            for entity in row['entities']:
                seekdb_client.insert("feedback_stat", {
                    "stat_date": stat_date,
                    "entity_type": entity['entity_type'],
                    "entity_value": entity['entity_value'],
                    "feedback_count": row['feedback_count'],
                    "ratio": row['ratio']
                })
                inserted_count += 1
        
        logger.info(f"成功存储 {inserted_count} 条统计结果")
        
    except Exception as e:
        logger.error(f"存储统计结果失败: {e}")


def invoke_coze_analysis(stat_data, stat_date):
    """
    调用Coze智能Agent进行分析总结
    对应架构图中的“智能Agent分析总结”
    
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
        
        logger.info("Coze智能Agent成功生成分析总结")
        return analysis_content
        
    except Exception as e:
        logger.error(f"Coze智能Agent分析总结失败: {e}")
        return None


def store_analysis_result(analysis_text, stat_date):
    """
    存储分析总结结果
    对应架构图中的“总结存储”
    
    Args:
        analysis_text (str): 分析总结文本
        stat_date (str): 统计日期
    """
    try:
        # 先删除当天已有的分析结果
        delete_sql = f"DELETE FROM ai_analysis_result WHERE stat_date = '{stat_date}'"
        seekdb_client.execute_sql(delete_sql)
        
        # 插入新的分析结果
        seekdb_client.insert("ai_analysis_result", {
            "stat_date": stat_date,
            "analysis_text": analysis_text
        })
        
        logger.info(f"成功存储 {stat_date} 的分析总结结果")
        
    except Exception as e:
        logger.error(f"存储分析总结结果失败: {e}")


def generate_daily_summary(stat_date):
    """
    生成每日分析总结
    对应架构图中的“分析总结”完整流程
    
    Args:
        stat_date (str): 统计日期
    """
    logger.info(f"开始生成 {stat_date} 的分析总结")
    
    # 1. 生成统计结果
    stat_df = generate_statistics(stat_date)
    
    if stat_df.empty:
        logger.info(f"{stat_date} 无数据，跳过分析总结")
        return
    
    # 2. 存储统计结果
    store_statistics(stat_df, stat_date)
    
    # 3. 转换统计数据为字典格式
    stat_data = []
    for _, row in stat_df.iterrows():
        stat_item = {
            "entities": row['entities'],
            "feedback_count": row['feedback_count'],
            "ratio": row['ratio']
        }
        stat_data.append(stat_item)
    
    # 4. 调用Coze进行智能分析
    analysis_text = invoke_coze_analysis(stat_data, stat_date)
    
    if analysis_text:
        # 5. 存储分析总结结果
        store_analysis_result(analysis_text, stat_date)
        logger.info(f"{stat_date} 分析总结完成")
    else:
        logger.warning(f"{stat_date} 分析总结生成失败")


def generate_system_metrics(stat_date):
    """
    生成系统运行指标
    
    Args:
        stat_date (str): 统计日期
        
    Returns:
        dict: 系统指标
    """
    try:
        # 1. 总反馈量
        total_feedback_sql = f"""
        SELECT COUNT(*) AS total_count 
        FROM customer_feedback 
        WHERE DATE(create_time) = '{stat_date}'
        """
        total_feedback = seekdb_client.query_sql(total_feedback_sql).iloc[0]['total_count']
        
        # 2. 已打标反馈量
        tagged_feedback_sql = f"""
        SELECT COUNT(DISTINCT f.feedback_id) AS tagged_count
        FROM feedback_entity_relation f
        JOIN customer_feedback c ON f.feedback_id = c.feedback_id
        WHERE DATE(c.create_time) = '{stat_date}'
        """
        tagged_feedback = seekdb_client.query_sql(tagged_feedback_sql).iloc[0]['tagged_count']
        
        # 3. Coze调用量
        coze_call_sql = f"""
        SELECT COUNT(*) AS coze_call_count
        FROM entity_precipitation_log l
        JOIN customer_feedback c ON l.feedback_id = c.feedback_id
        WHERE DATE(c.create_time) = '{stat_date}'
        """
        coze_call = seekdb_client.query_sql(coze_call_sql).iloc[0]['coze_call_count']
        
        # 4. 新实体沉淀量
        new_entity_sql = f"""
        SELECT COUNT(*) AS new_entity_count
        FROM entity_vector_lib
        WHERE DATE(create_time) = '{stat_date}'
        """
        new_entity = seekdb_client.query_sql(new_entity_sql).iloc[0]['new_entity_count']
        
        metrics = {
            "stat_date": stat_date,
            "total_feedback": total_feedback,
            "tagged_feedback": tagged_feedback,
            "tag_rate": tagged_feedback / total_feedback if total_feedback > 0 else 0,
            "coze_call_count": coze_call,
            "coze_call_rate": coze_call / total_feedback if total_feedback > 0 else 0,
            "new_entity_count": new_entity
        }
        
        logger.info(f"系统指标生成完成: {metrics}")
        return metrics
        
    except Exception as e:
        logger.error(f"生成系统指标失败: {e}")
        return {}


# ---------------------- 主函数 ----------------------

def main():
    """
    主函数
    """
    logger.info("===== 客服反馈分析总结系统启动 =====")
    
    try:
        stat_date = ANALYSIS_DATE
        
        # 生成分析总结
        generate_daily_summary(stat_date)
        
        # 生成系统运行指标
        metrics = generate_system_metrics(stat_date)
        logger.info(f"系统运行指标: {metrics}")
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
    finally:
        logger.info("===== 客服反馈分析总结系统结束 =====")


if __name__ == "__main__":
    main()