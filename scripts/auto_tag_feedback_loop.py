#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
客服反馈自动打标主脚本
对应架构图中的“自动打标”流程：
- 读取待打标明细
- 向量化反馈明细（SeekDB自动完成）
- 匹配打标（SeekDB混合检索）
- 置信度>80%直接打标
- 低置信度触发智能Agent识别
- 重新打标并沉淀到标签向量库
"""

import os
import sys
import json
import requests
import logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import pymysql
import numpy as np
from sentence_transformers import SentenceTransformer

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/tag_loop.log')),
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
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.8))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 1000))

# 向量生成配置
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', 384))

# 初始化向量生成模型
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info(f"向量生成模型初始化成功: {EMBEDDING_MODEL}")
except Exception as e:
    logger.error(f"向量生成模型初始化失败: {e}")
    sys.exit(1)

# ---------------------- 数据库客户端类 ----------------------
class DatabaseClient:
    def __init__(self, **config):
        self.config = config
        self.connection = None
        self.connect()
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            raise Exception(f"数据库连接失败: {e}")
    
    def query_sql(self, sql, params=None):
        """执行查询SQL并返回DataFrame"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return pd.DataFrame(result)
        except Exception as e:
            raise Exception(f"查询执行失败: {e}")
    
    def execute_sql(self, sql, params=None):
        """执行SQL语句（更新、删除等）"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            raise Exception(f"SQL执行失败: {e}")
    
    def insert(self, table, data):
        """插入数据到指定表"""
        if not data:
            return 0
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = list(data.values())
        
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute_sql(sql, values)

# ---------------------- 数据库客户端初始化 ----------------------
try:
    db_client = DatabaseClient(**SEEKDB_CONFIG)
    logger.info("数据库客户端初始化成功")
except Exception as e:
    logger.error(f"数据库客户端初始化失败: {e}")
    sys.exit(1)

# ---------------------- 核心函数 ----------------------

def invoke_coze_entity_recognize(feedback_text):
    """
    调用Coze智能Agent识别动态实体
    对应架构图中的“智能agent：显性/隐性标签、实体、关键词识别”
    
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
        
        logger.info(f"Coze智能Agent成功识别到 {len(entities)} 个实体")
        return entities
        
    except json.JSONDecodeError as e:
        logger.error(f"Coze返回结果JSON解析失败: {e}, 响应内容: {coze_result}")
        return []
    except Exception as e:
        logger.error(f"Coze智能Agent调用失败: {e}")
        return []


def generate_embedding(text):
    """
    生成文本向量
    
    Args:
        text (str): 输入文本
        
    Returns:
        str: 向量字符串
    """
    try:
        # 使用sentence-transformers生成向量
        embedding = embedding_model.encode(text, convert_to_numpy=True)
        # 转换为字符串格式，适应数据库存储
        embedding_str = ','.join(map(str, embedding.tolist()))
        return embedding_str
    except Exception as e:
        logger.error(f"向量生成失败: {e}")
        return None


def insert_entity_to_seekdb(entity_item):
    """
    将Coze识别的实体写入标签向量库
    对应架构图中的“标签向量库”和“去重标签向量库”
    
    Args:
        entity_item (dict): 实体信息字典
        
    Returns:
        tuple: (entity_id, confidence)
    """
    type_name = entity_item.get('type_name')
    entity_value = entity_item.get('entity_value')
    coze_confidence = entity_item.get('confidence', 0.95)
    
    if not type_name or not entity_value:
        logger.warning(f"实体信息不完整: {entity_item}")
        return None, None
    
    try:
        # 1. 新增实体类型（不存在则插入）
        type_sql = "SELECT type_id FROM dynamic_entity_type WHERE type_name = %s"
        type_result = db_client.query_sql(type_sql, params=[type_name])
        
        if type_result.empty:
            # 插入新的实体类型
            db_client.insert("dynamic_entity_type", {"type_name": type_name})
            type_result = db_client.query_sql(type_sql, params=[type_name])
            logger.info(f"新增实体类型: {type_name}")
        
        type_id = type_result['type_id'].iloc[0]
        
        # 2. 生成实体向量
        entity_text = f"{type_name}:{entity_value}"
        entity_vector = generate_embedding(entity_text)
        
        if not entity_vector:
            logger.error(f"实体向量生成失败: {entity_text}")
            return None, None
        
        # 3. 新增实体值（去重处理）
        entity_sql = "SELECT entity_id FROM entity_vector_lib WHERE type_id = %s AND entity_value = %s"
        entity_result = db_client.query_sql(entity_sql, params=[type_id, entity_value])
        
        if entity_result.empty:
            # 插入新的实体值
            db_client.insert("entity_vector_lib", {
                "type_id": type_id,
                "entity_value": entity_value,
                "entity_vector": entity_vector,
                "confidence": coze_confidence
            })
            entity_result = db_client.query_sql(entity_sql, params=[type_id, entity_value])
            logger.info(f"新增实体值: {type_name}:{entity_value}")
        
        entity_id = entity_result['entity_id'].iloc[0]
        
        return entity_id, coze_confidence
        
    except Exception as e:
        logger.error(f"实体写入数据库失败: {e}")
        return None, None


def seekdb_match_entity(feedback_id):
    """
    混合检索匹配实体
    对应架构图中的“匹配打标”
    
    Args:
        feedback_id (str): 反馈ID
        
    Returns:
        list: 匹配结果列表
    """
    try:
        # 获取反馈的向量和文本
        feedback_sql = """
        SELECT feedback_text, feedback_vector 
        FROM customer_feedback 
        WHERE feedback_id = %s
        """
        feedback_result = db_client.query_sql(feedback_sql, params=[feedback_id])
        
        if feedback_result.empty:
            logger.warning(f"反馈ID不存在: {feedback_id}")
            return []
        
        feedback_text = feedback_result['feedback_text'].iloc[0]
        feedback_vector = feedback_result['feedback_vector'].iloc[0]
        
        # 混合检索：向量相似度 + 关键词匹配
        match_sql = f"""
        SELECT 
            e.entity_id, 
            t.type_name, 
            e.entity_value,
            VECTOR_SIMILARITY(e.entity_vector, %s) AS match_confidence
        FROM 
            entity_vector_lib e
        JOIN 
            dynamic_entity_type t ON e.type_id = t.type_id
        WHERE 
            VECTOR_SIMILARITY(e.entity_vector, %s) > 0.5
            AND MATCH(e.entity_value) AGAINST(%s IN NATURAL LANGUAGE MODE)
        ORDER BY 
            match_confidence DESC
        """
        
        match_result = db_client.query_sql(match_sql, params=[feedback_vector, feedback_vector, feedback_text]).to_dict('records')
        logger.info(f"匹配到 {len(match_result)} 个实体")
        
        return match_result
        
    except Exception as e:
        logger.error(f"实体匹配失败: {e}")
        return []


def write_tag_result(feedback_id, entity_id, match_confidence):
    """
    写入反馈明细+打标结果
    对应架构图中的“反馈明细+打标结果”
    
    Args:
        feedback_id (str): 反馈ID
        entity_id (str): 实体ID
        match_confidence (float): 匹配置信度
    """
    try:
        db_client.insert("feedback_entity_relation", {
            "feedback_id": feedback_id,
            "entity_id": entity_id,
            "match_confidence": match_confidence
        })
        logger.info(f"反馈 {feedback_id} 打标成功，实体 {entity_id}，置信度 {match_confidence:.2f}")
    except Exception as e:
        logger.error(f"打标结果写入失败: {e}")


def write_re_tag_detail(feedback_id, entity_id, coze_confidence):
    """
    写入重新打标明细
    对应架构图中的“重新打标明细”
    
    Args:
        feedback_id (str): 反馈ID
        entity_id (str): 实体ID
        coze_confidence (float): Coze识别置信度
    """
    try:
        db_client.insert("entity_precipitation_log", {
            "feedback_id": feedback_id,
            "entity_id": entity_id,
            "coze_confidence": coze_confidence
        })
        logger.info(f"反馈 {feedback_id} 重新打标明细记录成功")
    except Exception as e:
        logger.error(f"重新打标明细写入失败: {e}")


def get_untagged_feedback(batch_size=BATCH_SIZE):
    """
    获取待打标明细，并为没有向量的反馈生成向量
    对应架构图中的“待打标明细”
    
    Args:
        batch_size (int): 批次大小
        
    Returns:
        DataFrame: 未打标的反馈数据
    """
    untagged_sql = """
    SELECT 
        feedback_id, 
        feedback_text, 
        feedback_vector
    FROM 
        customer_feedback 
    WHERE 
        feedback_id NOT IN (SELECT feedback_id FROM feedback_entity_relation)
    LIMIT %s
    """
    
    try:
        untagged_df = db_client.query_sql(untagged_sql, params=[batch_size])
        logger.info(f"获取到 {len(untagged_df)} 条待打标反馈")
        
        # 为没有向量的反馈生成向量
        for index, row in untagged_df.iterrows():
            if not row['feedback_vector'] or pd.isna(row['feedback_vector']):
                # 生成向量
                feedback_vector = generate_embedding(row['feedback_text'])
                if feedback_vector:
                    # 更新数据库中的向量
                    update_sql = """
                    UPDATE customer_feedback 
                    SET feedback_vector = %s 
                    WHERE feedback_id = %s
                    """
                    db_client.execute_sql(update_sql, params=[feedback_vector, row['feedback_id']])
                    logger.info(f"为反馈 {row['feedback_id']} 生成并更新向量")
        
        return untagged_df
    except Exception as e:
        logger.error(f"获取待打标反馈失败: {e}")
        return pd.DataFrame()


def process_feedback_batch():
    """
    处理一批反馈的打标
    对应架构图中的“自动打标”完整流程
    """
    untagged_df = get_untagged_feedback()
    
    if untagged_df.empty:
        logger.info("无待打标明细，流程结束")
        return
    
    processed_count = 0
    success_count = 0
    coze_trigger_count = 0
    
    for _, row in untagged_df.iterrows():
        feedback_id = row['feedback_id']
        feedback_text = row['feedback_text']
        
        try:
            # 1. SeekDB匹配打标
            match_result = seekdb_match_entity(feedback_id)
            
            if match_result:
                # 2. 判断置信度
                max_confidence = max([item['match_confidence'] for item in match_result])
                
                if max_confidence >= CONFIDENCE_THRESHOLD:
                    # 高置信度：直接打标
                    best_match = [item for item in match_result if item['match_confidence'] == max_confidence][0]
                    write_tag_result(feedback_id, best_match['entity_id'], best_match['match_confidence'])
                    success_count += 1
                else:
                    # 低置信度：触发Coze智能Agent
                    logger.info(f"反馈 {feedback_id} 置信度不足 ({max_confidence:.2f})，触发智能Agent")
                    coze_entities = invoke_coze_entity_recognize(feedback_text)
                    coze_trigger_count += 1
                    
                    if coze_entities:
                        # 写入新实体并打标
                        for entity in coze_entities:
                            entity_id, coze_confidence = insert_entity_to_seekdb(entity)
                            if entity_id:
                                write_tag_result(feedback_id, entity_id, coze_confidence)
                                write_re_tag_detail(feedback_id, entity_id, coze_confidence)
                                success_count += 1
            else:
                # 无匹配结果：触发Coze智能Agent
                logger.info(f"反馈 {feedback_id} 无匹配标签，触发智能Agent")
                coze_entities = invoke_coze_entity_recognize(feedback_text)
                coze_trigger_count += 1
                
                if coze_entities:
                    # 写入新实体并打标
                    for entity in coze_entities:
                        entity_id, coze_confidence = insert_entity_to_seekdb(entity)
                        if entity_id:
                            write_tag_result(feedback_id, entity_id, coze_confidence)
                            write_re_tag_detail(feedback_id, entity_id, coze_confidence)
                            success_count += 1
            
            processed_count += 1
            
        except Exception as e:
            logger.error(f"处理反馈 {feedback_id} 时发生错误: {e}")
            continue
    
    # 记录批次处理结果
    logger.info(f"批次处理完成 - 总处理: {processed_count}, 成功: {success_count}, Coze触发: {coze_trigger_count}")


# ---------------------- 主函数 ----------------------

def main():
    """
    主函数
    """
    logger.info("===== 客服反馈自动打标系统启动 =====")
    
    try:
        process_feedback_batch()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
    finally:
        logger.info("===== 客服反馈自动打标系统结束 =====")


if __name__ == "__main__":
    main()