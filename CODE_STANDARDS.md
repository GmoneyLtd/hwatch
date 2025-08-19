# Python 代码规范指南

本文档定义了项目的 Python 代码规范，适用于 CodeBuddy 和其他代码审查工具。

## 基本规则

- **Python 版本**：3.13+
- **行长度**：最大 120 字符
- **缩进**：4 个空格（不使用制表符）
- **字符串引号**：优先使用双引号 `""`
- **文件长度**：单个文件不超过 500 行，超过时应拆分模块

## 类型注解

- **严格类型检查**：启用严格模式
- **可选类型**：使用 `| None` 语法代替 `Optional[T]`
- **类型别名**：对复杂类型使用 `type` 定义类型别名
- **泛型**：适当使用泛型提高代码类型安全性
- **必须为函数参数和返回值提供类型注解**

```python
# 不推荐
def process_data(data, options=None):
    pass

# 推荐
def process_data(data: list[str], options: dict[str, int] | None = None) -> bool:
    pass
```

## 导入规范

- **导入排序**：按标准库、第三方库、本地模块分组
- **禁止使用通配符导入**：不使用 `from module import *`
- **禁止未使用的导入**：删除未使用的导入语句
- **相对导入**：包内使用相对导入 `.module`

```python
# 标准库
import os
import sys
from collections.abc import Callable

# 第三方库
from loguru import logger

# 本地模块
from core.config import settings
```

## 文档规范

- **文档风格**：使用 Google 风格文档字符串
- **必须为公共函数、类和方法提供文档字符串**
- **文档摘要必须以句点结束**
- **参数和返回值必须在文档中说明**

```python
def calculate_average(numbers: list[float]) -> float:
    """计算数字列表的平均值。

    Args:
        numbers: 要计算平均值的数字列表

    Returns:
        列表中所有数字的平均值
    """
    return sum(numbers) / len(numbers)
```

## 命名规范

- **函数和变量**：`snake_case`
- **常量**：`UPPER_CASE`
- **类名**：`PascalCase`
- **私有成员**：使用单下划线前缀 `_private_var`

## 代码复杂度

- **函数长度**：不超过 50 行
- **圈复杂度**：不超过 10
- **嵌套层级**：不超过 4 层
- **参数数量**：不超过 5 个

## 现代 Python 特性

- **使用 f-strings** 进行字符串格式化
- **使用海象运算符** `:=` 简化代码
- **使用 `pathlib`** 代替 `os.path`
- **使用类型别名** 简化复杂类型
- **使用结构模式匹配** `match/case` 代替复杂的 if-elif 链

## 错误预防

- **检查未使用的变量和函数**
- **检查不必要的类型转换**
- **检查不必要的比较**
- **检查 f-string 格式化错误**

## 代码检查工具

- **ruff**：用于代码风格和质量检查
  - 规则集：E, W, F, I, B, UP, C4, RUF
- **basedpyright**：用于类型检查
  - 启用严格模式

## 自动修复

- 保存时自动修复简单问题
- 自动排序导入
- 自动格式化代码