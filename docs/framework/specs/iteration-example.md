# 迭代3 Spec - 文档版本控制

## 元信息
- **Spec名称**: 迭代3 Spec
- **类型**: 迭代
- **版本**: 1.0.0
- **前置条件**: 迭代1文档CRUD已完成，DocumentVersion模型已定义
- **输出产物**: DocumentVersionRepository + Service层版本管理 + API端点 + 单元测试
- **质量标准**: 测试覆盖率≥80%，版本创建/查询/回滚正确
- **执行状态文件**: `docs/execution/iteration-3-status.md`

## 依赖Skill
- 数据层开发Skill (`docs/skills/data-layer-skill.md`)
- 业务层开发Skill (`docs/skills/business-layer-skill.md`)
- API层开发Skill (`docs/skills/api-layer-skill.md`)

## PDCA执行步骤

### Plan (规划)
- **目标**: 实现文档版本管理(创建版本/查询历史/版本回滚)
- **输入**: DocumentVersion模型(已定义在models/__init__.py)
- **活动**:
  1. 定义DocumentVersionRepository接口
  2. 定义Service层版本管理方法
  3. 定义API端点(获取版本列表/获取版本详情/回滚)
  4. 编写测试用例清单
- **输出**: Repository接口 + 测试用例清单

### Do (执行)
- **输入**: Repository接口 + 测试用例清单
- **活动**:
  1. 实现DocumentVersionRepository(按文档查询版本/创建版本)
  2. 实现DocumentService.create_version(上传新版本文件)
  3. 实现DocumentService.rollback(回滚到指定版本)
  4. 实现API端点(/documents/{id}/versions, /documents/{id}/versions/{vid}/rollback)
  5. 每个方法用TDD: Red→Green→Refactor
- **输出**: 版本管理实现 + 单元测试

### Check (验证)
- **输入**: 版本管理代码 + 测试
- **活动**:
  1. 运行全部单元测试
  2. 验证版本创建后版本号递增
  3. 验证回滚后文档内容恢复
  4. 检查测试覆盖率
- **输出**: 测试报告

### Act (改进)
- **输入**: 测试报告
- **活动**:
  1. 补充缺失的测试
  2. 优化版本管理逻辑
  3. 记录TDD日志
- **输出**: 最终版版本管理 + TDD日志

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2025-01-XX | 初始版本 | ADE |
