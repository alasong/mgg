# 文档模板索引

## 项目规范
| 模板 | 用途 | 路径 |
|------|------|------|
| AGENT.MD模板 | 项目规范和架构管控 | `templates/agent-md-template.md` |

## Skill模板
| 模板 | 用途 | 路径 |
|------|------|------|
| 阶段Skill模板 | 定义开发阶段能力 | `templates/skill-phase-template.md` |
| 层面Skill模板 | 定义架构层面开发规范 | `templates/skill-layer-template.md` |
| 功能Skill模板 | 定义具体功能开发步骤 | `templates/skill-feature-template.md` |

## 过程文档模板
| 模板 | 用途 | 路径 |
|------|------|------|
| 迭代记录模板 | 记录迭代过程和结果 | `templates/iteration-template.md` |
| Skill执行日志模板 | 记录Skill执行情况 | `templates/skill-execution-log-template.md` |
| TDD执行日志模板 | 记录TDD循环过程 | `templates/tdd-log-template.md` |

## 使用方式

1. **复制模板**：将对应模板复制到项目文档目录
2. **填写内容**：根据实际情况填写模板内容
3. **版本管理**：纳入Git版本控制
4. **持续更新**：开发过程中实时更新

## 文档目录建议结构

```
docs/
├── architecture/              # 架构文档
│   ├── overview.md
│   ├── decisions/             # 架构决策记录(ADR)
│   │   ├── 001-[决策标题].md
│   │   └── 002-[决策标题].md
│   └── diagrams/              # 架构图
│
├── design/                    # 设计文档
│   ├── [模块名]-design.md
│   └── api/                   # API文档
│
├── development/               # 开发过程文档
│   ├── iteration-01.md        # 迭代记录
│   ├── iteration-02.md
│   ├── skill-logs/            # Skill执行日志
│   │   └── [skill-name]-log.md
│   └── tdd-logs/              # TDD执行日志
│       └── [feature-name]-tdd-log.md
│
├── testing/                   # 测试文档
│   ├── test-plan.md
│   ├── test-cases.md
│   └── test-reports/
│
└── deployment/                # 部署文档
    ├── deployment-guide.md
    └── release-notes/
```
