# 数据层开发Skill

## 元信息
- **Skill名称**: 数据层开发Skill
- **类型**: 层面
- **版本**: 1.0.0
- **所属架构层**: 数据访问层 (Repository)
- **前置条件**: 数据库Schema已设计，Alembic迁移已生成
- **输出产物**: Repository类 + 单元测试
- **质量标准**: 测试覆盖率≥80%，CRUD操作正确
- **执行状态文件**: `docs/execution/data-layer-status.md`

## PDCA执行步骤

### Plan (规划)
- **目标**: 为每个实体实现Repository，封装数据库操作
- **输入**: SQLAlchemy模型定义
- **活动**:
  1. 定义Repository接口(抽象基类)
  2. 列出每个Repository需要的CRUD方法
  3. 编写测试用例清单
- **输出**: Repository接口定义 + 测试用例清单
- **验证**: 接口覆盖所有业务场景

### Do (执行)
- **输入**: Repository接口 + 测试用例清单
- **活动**:
  1. 实现BaseRepository(通用CRUD)
  2. 按实体实现具体Repository
  3. 每个方法用TDD: Red→Green→Refactor
  4. 编写单元测试(使用pytest + transaction回滚)
- **输出**: Repository实现 + 单元测试
- **验证**: 所有测试通过

### Check (验证)
- **输入**: Repository实现 + 测试
- **活动**:
  1. 运行全部单元测试
  2. 检查测试覆盖率
  3. 验证CRUD操作正确性
  4. 验证异常处理
- **输出**: 测试报告
- **验证**: 覆盖率≥80%，无失败测试

### Act (改进)
- **输入**: 测试报告
- **活动**:
  1. 补充缺失的测试
  2. 优化Repository代码
  3. 记录TDD日志
- **输出**: 最终版Repository + TDD日志
- **验证**: 代码质量达标

## TDD要求
- **测试框架**: pytest
- **数据库**: 测试用SQLite或PostgreSQL test schema
- **Mock策略**: 不Mock数据库，用真实DB + transaction回滚
- **测试隔离**: 每个测试独立事务，测试后回滚

## 注意事项
- Repository只负责数据访问，不含业务逻辑
- 使用SQLAlchemy ORM，不写原生SQL(除非性能需要)
- 分页查询必须支持
- 软删除用status字段，不用物理删除

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2025-01-XX | 初始版本 | ADE |
