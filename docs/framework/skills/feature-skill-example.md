# ES搜索集成Skill

## 元信息
- **Skill名称**: ES搜索集成Skill
- **类型**: 功能
- **版本**: 1.0.0
- **所属架构层**: 数据访问层(Repository) + 业务服务层(Service)
- **前置条件**: ES客户端已封装(utils/es_client.py)，迭代1文档CRUD已完成
- **输出产物**: DocumentESRepository + Service层ES集成 + 单元测试
- **质量标准**: 测试覆盖率≥80%，搜索响应<2s，搜索结果与DB一致
- **执行状态文件**: `docs/execution/es-search-integration-status.md`

## PDCA执行步骤

### Plan (规划)
- **目标**: 用ES替换DB模糊搜索，文档CRUD同步到ES索引
- **输入**: 现有DocumentRepository.search_by_title(用DB ilike)
- **活动**:
  1. 定义DocumentESRepository接口(index/update/delete/search)
  2. 定义ES索引mapping(中文分词: ik_max_word/ik_smart)
  3. 编写测试用例清单
- **输出**: ES Repository接口 + 测试用例清单
- **验证**: 接口覆盖搜索/索引/删除场景

### Do (执行)
- **输入**: ES Repository接口 + 测试用例清单
- **活动**:
  1. 实现DocumentESRepository(索引mapping/CRUD同步/全文搜索)
  2. 更新DocumentService.search_documents调用ES而非DB
  3. 更新DocumentService.create_document同步写入ES
  4. 更新DocumentService.delete_document同步删除ES
  5. 每个方法用TDD: Red→Green→Refactor
- **输出**: ES Repository实现 + Service层集成 + 单元测试
- **验证**: 所有测试通过

### Check (验证)
- **输入**: ES集成代码 + 测试
- **活动**:
  1. 运行全部单元测试
  2. 验证搜索返回结果正确(标题/描述/标签多字段搜索)
  3. 验证文档创建/删除后ES索引同步
  4. 检查测试覆盖率
- **输出**: 测试报告
- **验证**: 覆盖率≥80%，无失败测试

### Act (改进)
- **输入**: 测试报告
- **活动**:
  1. 补充缺失的测试
  2. 优化ES查询性能
  3. 记录TDD日志
  4. 更新迭代记录文档
- **输出**: 最终版ES集成 + TDD日志 + 迭代记录
- **验证**: 代码质量达标

## TDD要求
- **测试框架**: pytest + pytest-asyncio
- **Mock策略**: Mock ES客户端(不依赖真实ES服务)
- **测试隔离**: 每个测试独立，使用asyncio fixture

## 功能分解
| 功能 | TDD步骤 | 状态 |
|------|---------|------|
| ES索引mapping创建 | Red→Green→Refactor | 待开发 |
| 文档索引(index) | Red→Green→Refactor | 待开发 |
| 文档更新(update) | Red→Green→Refactor | 待开发 |
| 文档删除(delete) | Red→Green→Refactor | 待开发 |
| 全文搜索(search) | Red→Green→Refactor | 待开发 |
| Service层集成 | Red→Green→Refactor | 待开发 |

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2025-01-XX | 初始版本 | ADE |
