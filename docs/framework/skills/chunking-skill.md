# 分块系统Skill

## 元信息
- **类型**: 功能
- **前置条件**: document-parser-skill, data-layer-skill
- **输出产物**: 分块服务、分块结果存储、API接口
- **质量标准**: 分块质量可用，处理速度>1000字/秒
- **执行状态文件**: `docs/execution/chunking-skill-status.md`

## 简介

分块系统Skill封装了文档文本的分块能力，支持3种基础分块策略：
1. **固定长度分块** - 按固定字符数分割，支持重叠
2. **段落分块** - 按空行/段落分割
3. **标题分块** - 按标题层级分割

## 分块策略详解

### 1. 固定长度分块 (Fixed-Size Chunking)

**原理**: 按固定字符数分割文本，支持块间重叠以保持上下文

**参数**:
- `chunk_size`: 每块字符数（默认500）
- `overlap`: 重叠字符数（默认50）

**适用场景**: 通用文档、无明确结构的文本

**示例**:
```
文本: "这是一段很长的文本内容..."
chunk_size=100, overlap=20
→ Chunk1: "这是一段很长的文本内容...[100字符]"
→ Chunk2: "[最后20字符]下一段文本内容...[80字符]"
```

### 2. 段落分块 (Paragraph Chunking)

**原理**: 按空行/段落分割文本，每个段落作为一个块

**参数**:
- `separator`: 段落分隔符（默认`\n\n`）
- `min_length`: 最小块长度（默认50）
- `max_length`: 最大块长度（默认2000）

**适用场景**: 文章、报告、有明确段落结构的文档

**示例**:
```
文本: "第一段内容...\n\n第二段内容...\n\n第三段内容..."
→ Chunk1: "第一段内容..."
→ Chunk2: "第二段内容..."
→ Chunk3: "第三段内容..."
```

### 3. 标题分块 (Heading Chunking)

**原理**: 按标题层级分割文本，每个标题下的内容作为一个块

**参数**:
- `heading_pattern`: 标题匹配模式（默认`^#{1,6}\s+`）
- `include_heading`: 是否在块中包含标题（默认True）

**适用场景**: Markdown文档、有标题结构的文档

**示例**:
```
文本: "# 第一章\n内容...\n## 1.1 节\n内容...\n# 第二章\n内容..."
→ Chunk1: "# 第一章\n内容...\n## 1.1 节\n内容..."
→ Chunk2: "# 第二章\n内容..."
```

## PDCA执行步骤

### Plan (规划)

**目标**: 设计分块系统架构和接口

**活动**:
1. 定义分块服务接口 (`ChunkingService`)
2. 定义分块结果模型 (`Chunk`)
3. 设计分块策略注册表
4. 定义分块质量评估方法

**输出**:
- 分块服务接口定义
- 分块结果模型
- 策略注册表设计

**验证标准**:
- 接口清晰可扩展
- 模型覆盖所有分块场景
- 策略注册表支持动态添加

### Do (执行)

**目标**: TDD实现分块功能

**活动**:
1. 创建分块服务骨架
2. TDD实现固定长度分块
3. TDD实现段落分块
4. TDD实现标题分块
5. 实现分块结果存储
6. 实现分块质量评估

**TDD循环**:
```
Red: 编写分块测试用例
Green: 最小实现分块逻辑
Refactor: 优化代码结构
```

**输出**:
- `src/services/chunking_service.py`
- `src/models/chunk.py`
- `src/strategies/fixed_chunking.py`
- `src/strategies/paragraph_chunking.py`
- `src/strategies/heading_chunking.py`
- 单元测试

**验证标准**:
- 所有测试通过
- 分块质量可用
- 处理速度>1000字/秒

### Check (验证)

**目标**: 验证分块质量和性能

**活动**:
1. 执行单元测试
2. 执行集成测试
3. 分块质量评估（人工抽样）
4. 性能基准测试
5. 边界情况测试

**输出**:
- 测试报告
- 分块质量评估报告
- 性能基准报告

**验证标准**:
- 测试覆盖率≥80%
- 分块质量评分>80%
- 处理速度>1000字/秒

### Act (改进)

**目标**: 优化分块策略，沉淀经验

**活动**:
1. 分析分块质量问题
2. 优化分块参数
3. 处理边界情况
4. 沉淀分块经验到Skill
5. 更新执行状态

**输出**:
- 优化后的代码
- 更新的Skill文档
- 执行状态更新

**验证标准**:
- 所有问题已解决
- Skill文档完整
- 执行状态最新

## 接口定义

```python
class ChunkingStrategy(ABC):
    """分块策略基类"""
    
    @abstractmethod
    def chunk(self, text: str, **kwargs) -> list[Chunk]:
        """将文本分块"""
        pass

class FixedSizeChunking(ChunkingStrategy):
    """固定长度分块"""
    def chunk(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[Chunk]:
        pass

class ParagraphChunking(ChunkingStrategy):
    """段落分块"""
    def chunk(self, text: str, separator: str = "\n\n", min_length: int = 50, max_length: int = 2000) -> list[Chunk]:
        pass

class HeadingChunking(ChunkingStrategy):
    """标题分块"""
    def chunk(self, text: str, heading_pattern: str = r"^#{1,6}\s+", include_heading: bool = True) -> list[Chunk]:
        pass

class ChunkingService:
    """分块服务"""
    
    def __init__(self):
        self.strategies = {}
        self.register_strategy("fixed", FixedSizeChunking())
        self.register_strategy("paragraph", ParagraphChunking())
        self.register_strategy("heading", HeadingChunking())
    
    def register_strategy(self, name: str, strategy: ChunkingStrategy):
        """注册分块策略"""
        pass
    
    def chunk(self, text: str, strategy: str = "fixed", **kwargs) -> list[Chunk]:
        """执行分块"""
        pass

class Chunk:
    """分块结果"""
    id: str           # 块ID
    document_id: str  # 文档ID
    content: str      # 块内容
    index: int        # 块索引
    metadata: dict    # 元数据
```

## 测试用例

```python
# 固定长度分块测试
def test_fixed_chunking_basic():
    """测试基础固定长度分块"""
    pass

def test_fixed_chunking_overlap():
    """测试重叠分块"""
    pass

def test_fixed_chunking_short_text():
    """测试短文本分块"""
    pass

# 段落分块测试
def test_paragraph_chunking_basic():
    """测试基础段落分块"""
    pass

def test_paragraph_chunking_empty_paragraphs():
    """测试空段落处理"""
    pass

def test_paragraph_chunking_long_paragraph():
    """测试长段落分割"""
    pass

# 标题分块测试
def test_heading_chunking_basic():
    """测试基础标题分块"""
    pass

def test_heading_chunking_nested_headings():
    """测试嵌套标题分块"""
    pass

def test_heading_chunking_no_headings():
    """测试无标题文本"""
    pass

# 性能测试
def test_chunking_performance():
    """测试分块性能"""
    pass
```

## 依赖关系
- 依赖Skill: document-parser-skill (解析后分块)
- 依赖Skill: data-layer-skill (存储分块结果)
- 被依赖Skill: vector-embedding-skill (分块后向量化)

## 注意事项
1. **空文本**: 需处理空文本输入
2. **超长文本**: 需限制单次分块大小
3. **编码问题**: 处理各种编码的文本
4. **分块质量**: 提供分块质量评估方法
5. **策略扩展**: 支持动态添加新策略
