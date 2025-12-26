-- 客服反馈自动打标系统 - 数据库初始化脚本

-- 1. 全量客服反馈明细（对应架构图中的“全量客服反馈明细”）
CREATE TABLE customer_feedback (
  feedback_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  feedback_text TEXT NOT NULL,
  user_id VARCHAR(64),
  create_time DATETIME DEFAULT NOW(),
  feedback_vector VECTOR(384) GENERATED ALWAYS AS (AI_EMBED(feedback_text)) STORED
);

-- 创建向量索引
CREATE INDEX idx_feedback_vector ON customer_feedback (feedback_vector) USING HNSW;

-- 创建文本索引（用于关键词匹配）
CREATE FULLTEXT INDEX idx_feedback_text ON customer_feedback (feedback_text);

-- 2. 动态实体类型表（对应架构图中的“标签类型”）
CREATE TABLE dynamic_entity_type (
  type_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  type_name VARCHAR(64) UNIQUE NOT NULL,
  create_time DATETIME DEFAULT NOW()
);

-- 3. 标签向量库（对应架构图中的“标签向量库”）
CREATE TABLE entity_vector_lib (
  entity_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  type_id VARCHAR(32),
  entity_value VARCHAR(128) NOT NULL,
  entity_vector VECTOR(384) GENERATED ALWAYS AS (AI_EMBED(CONCAT(type_name, ':', entity_value))) STORED,
  confidence FLOAT DEFAULT 0.95,
  create_time DATETIME DEFAULT NOW(),
  FOREIGN KEY (type_id) REFERENCES dynamic_entity_type(type_id),
  UNIQUE (type_id, entity_value)
);

-- 创建向量索引
CREATE INDEX idx_entity_vector ON entity_vector_lib (entity_vector) USING HNSW;

-- 创建文本索引
CREATE FULLTEXT INDEX idx_entity_value ON entity_vector_lib (entity_value);

-- 4. 反馈-实体关联表（对应架构图中的“反馈明细+打标结果”）
CREATE TABLE feedback_entity_relation (
  relation_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  feedback_id VARCHAR(32),
  entity_id VARCHAR(32),
  match_confidence FLOAT,
  create_time DATETIME DEFAULT NOW(),
  FOREIGN KEY (feedback_id) REFERENCES customer_feedback(feedback_id),
  FOREIGN KEY (entity_id) REFERENCES entity_vector_lib(entity_id)
);

-- 创建索引
CREATE INDEX idx_feedback_entity ON feedback_entity_relation (feedback_id);
CREATE INDEX idx_entity_feedback ON feedback_entity_relation (entity_id);

-- 5. 实体沉淀日志表（对应架构图中的“重新打标明细”）
CREATE TABLE entity_precipitation_log (
  log_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  feedback_id VARCHAR(32),
  entity_id VARCHAR(32),
  coze_confidence FLOAT,
  create_time DATETIME DEFAULT NOW(),
  FOREIGN KEY (feedback_id) REFERENCES customer_feedback(feedback_id),
  FOREIGN KEY (entity_id) REFERENCES entity_vector_lib(entity_id)
);

-- 创建索引
CREATE INDEX idx_precipitation_feedback ON entity_precipitation_log (feedback_id);

-- 6. 统计结果表（对应架构图中的“统计结果”）
CREATE TABLE feedback_stat (
  stat_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  stat_date DATE NOT NULL,
  entity_type VARCHAR(64) NOT NULL,
  entity_value VARCHAR(128) NOT NULL,
  feedback_count INT NOT NULL,
  ratio FLOAT,
  create_time DATETIME DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_stat_date ON feedback_stat (stat_date);
CREATE INDEX idx_stat_type ON feedback_stat (entity_type);

-- 7. AI分析总结表（对应架构图中的“总结存储”）
CREATE TABLE ai_analysis_result (
  analysis_id VARCHAR(32) PRIMARY KEY DEFAULT (UUID()),
  stat_date DATE NOT NULL,
  analysis_text TEXT NOT NULL,
  create_time DATETIME DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_analysis_date ON ai_analysis_result (stat_date);

-- 插入示例数据（可选）
INSERT INTO dynamic_entity_type (type_name) VALUES 
('业务类型'),
('产品大类'),
('具体产品'),
('问题现象'),
('问题特征');

-- 插入示例实体（可选）
INSERT INTO entity_vector_lib (type_id, entity_value) 
SELECT 
  (SELECT type_id FROM dynamic_entity_type WHERE type_name = '业务类型'),
  '报障'
UNION ALL
SELECT 
  (SELECT type_id FROM dynamic_entity_type WHERE type_name = '具体产品'),
  '益之源净水器'
UNION ALL
SELECT 
  (SELECT type_id FROM dynamic_entity_type WHERE type_name = '问题现象'),
  '滤芯换完报警';