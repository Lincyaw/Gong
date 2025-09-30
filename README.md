# Microservice Simulation Platform

一个高度可配置、动态化的微服务模拟环境生成平台，专为AIOps研究和LLM Agent训练设计。

## 🎯 项目目标

- **AIOps 研究**: 提供可控、可复现的实验环境，用于测试故障检测、根因分析等算法
- **LLM Agent 训练**: 构建接近真实的数字沙箱，为运维领域的LLM Agent提供训练环境
- **系统工程验证**: 支持在隔离环境中进行容量规划、压测和混沌测试

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│   用户交互层 (CLI, Web UI, REST API)                        │
│   ┌─────────────────┐                                       │
│   │   LLM 架构师    │                                       │
│   └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│   动态性注入层                                               │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│   │ 流量生成器  │ │ 混沌工程    │ │ 场景管理器          │   │
│   └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│   服务构造与编排层                                           │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│   │ 服务定义器  │ │ 代码生成器  │ │ 部署编排器          │   │
│   └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│   模板库                                                     │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│   │ 代码模板    │ │ 行为函数    │ │ 故障注入属性        │   │
│   └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- uv (Python包管理器)
- Kubernetes集群 (可选，用于生产部署)
- Docker (可选，用于构建镜像)

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd microservice-simulation-platform

# 使用 uv 安装依赖
uv sync

# 或者使用 pip
pip install -e .
```

### 启动平台

```bash
# 方式1: 使用开发脚本 (推荐)
python scripts/start-dev.py server

# 方式2: 直接启动API服务器
uv run python src/platform/api/main.py

# 方式3: 使用入口点
uv run platform-server
```

### 运行演示

```bash
# 运行演示测试
make demo

# 或者直接运行
uv run pytest tests/integration/test_demo.py -v
```

### 使用CLI

```bash
# 查看帮助
uv run simulation-platform --help

# 使用自然语言创建模拟环境
uv run simulation-platform create --prompt "创建一个三层电商应用，包括用户服务、订单服务和产品服务"

# 使用YAML配置文件创建
uv run simulation-platform create --spec-file examples/ecommerce-simulation.yaml

# 查看模拟环境状态
uv run simulation-platform status <simulation-id>

# 列出所有模拟环境
uv run simulation-platform list

# 删除模拟环境
uv run simulation-platform delete <simulation-id>
```

## 📋 核心功能

### 1. 声明式服务定义

使用YAML定义微服务架构：

```yaml
services:
  - name: order-service
    replicas: 3
    dependencies:
      services: ["user-service", "product-service"]
      datastores:
        - name: orders-db
          type: postgres
          provisioning:
            mode: dynamic
    endpoints:
      - path: /v1/orders
        method: POST
        workflow:
          - name: validate_user
            template: io/http_api_call
            params:
              target_service: user-service
              path: "/v1/users/{body.user_id}"
```

### 2. 模板化代码生成

支持多种内置模板：

- `io/http_api_call`: HTTP API调用
- `io/postgres_query`: 数据库查询
- `security/jwt_validation`: JWT令牌验证
- `control_flow/return_response`: 返回HTTP响应

### 3. 故障注入

在工作流中注入各种故障：

```yaml
workflow:
  - name: database_query
    template: io/postgres_query
    inject_faults:
      - type: latency
        probability: 0.1
        value: "normal(150, 20)"
      - type: error
        probability: 0.02
        value: "database_timeout"
```

### 4. 动态场景编排

定义时间线事件：

```yaml
scenario:
  events:
    - timestamp: "5m"
      type: traffic
      config:
        type: ramp
        params:
          start_users: 10
          end_users: 100
    - timestamp: "10m"
      type: chaos
      config:
        type: pod-delete
        target:
          service: order-service
```

## 🔧 开发指南

### 项目结构

```
src/platform/
├── core/           # 核心领域模型和接口
├── templates/      # 模板库系统
├── generator/      # 代码生成引擎
├── orchestrator/   # 部署编排器
├── chaos/          # 混沌工程引擎
├── traffic/        # 流量生成器
├── llm/           # LLM架构师
├── api/           # REST API层
└── utils/         # 工具类
```

### 添加新模板

```python
from gong.templates.base import BaseTemplate

# 定义新模板
template = BaseTemplate(
    name="custom/my_template",
    template_code="# Your Jinja2 template code here",
    input_schema={"param1": "str", "param2": "int"},
    output_schema={"result": "dict"}
)

# 注册模板
registry = get_dependencies().template_registry
await registry.register_template(template)
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行单元测试
uv run pytest tests/unit/

# 运行集成测试
uv run pytest tests/integration/

# 生成覆盖率报告
uv run pytest --cov=platform --cov-report=html
```

### 代码质量检查

```bash
# 格式化代码
uv run black src/ tests/
uv run isort src/ tests/

# 类型检查
uv run mypy src/

# 代码检查
uv run ruff check src/ tests/
```

## 📚 API文档

启动服务后访问 `http://localhost:8000/docs` 查看自动生成的API文档。

### 主要端点

- `POST /api/v1/simulations` - 创建模拟环境
- `GET /api/v1/simulations/{id}` - 获取模拟环境状态
- `DELETE /api/v1/simulations/{id}` - 删除模拟环境
- `POST /api/v1/simulations/{id}/actions` - 执行操作 (供LLM Agent使用)
- `GET /api/v1/templates` - 列出可用模板

## 🎯 使用场景

### AIOps研究

```bash
# 创建包含故障注入的电商环境
uv run simulation-platform create --prompt "创建电商环境，在订单服务中注入数据库超时故障"

# 监控和分析故障传播
kubectl logs -n sim-12345678 -l app=order-service
```

### LLM Agent训练

```python
import httpx

# Agent通过API与环境交互
async with httpx.AsyncClient() as client:
    # 查询系统状态
    response = await client.get(f"http://platform:8000/api/v1/simulations/{sim_id}")
    
    # 执行诊断操作
    action = {
        "action_type": "kubectl_logs",
        "target": "order-service",
        "params": {"lines": 100}
    }
    response = await client.post(f"http://platform:8000/api/v1/simulations/{sim_id}/actions", json=action)
```

### 系统验证

```yaml
# 定义压测场景
scenario:
  events:
    - timestamp: "0s"
      type: traffic
      config:
        type: constant
        params:
          users: 100
          duration: "30m"
    - timestamp: "15m"
      type: chaos
      config:
        type: network-latency
        params:
          latency: "500ms"
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [Kubernetes](https://kubernetes.io/) - 容器编排平台
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库
- [Jinja2](https://jinja.palletsprojects.com/) - 模板引擎