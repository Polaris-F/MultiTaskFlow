# 版本管理指南

本文档记录了 MultiTaskFlow 项目中所有需要更新版本号的位置。

## 🎯 唯一版本源

**`multitaskflow/__init__.py`** 中的 `__version__` 是项目的唯一版本源。

```python
__version__ = '1.0.5'  # ← 更新这里
```

## 📁 需要手动更新的位置

更新版本时，请检查以下位置：

| 文件 | 说明 | 备注 |
|------|------|------|
| `pyproject.toml` (L7) | PyPI 包版本 | **必须更新** |
| `multitaskflow/__init__.py` (L19) | Python 模块版本 | **必须更新** |
| `multitaskflow/web/frontend/src/components/Header.tsx` (L22) | 前端 UI 显示版本 | **必须更新** |

## 🔄 自动引用版本的位置

以下位置会自动从 `__version__` 获取版本：

| 文件 | 说明 |
|------|------|
| `multitaskflow/web/server.py` | FastAPI 版本 + 启动信息 |

## 📝 更新流程

1. **更新版本号**
   ```bash
   # 修改以下文件中的版本号
   pyproject.toml
   multitaskflow/__init__.py
   multitaskflow/web/frontend/src/components/Header.tsx
   ```

2. **更新 CHANGELOG.md**
   ```markdown
   ## [x.x.x] - 日期
   
   ### 新功能
   - 新功能描述
   
   ### 修复
   - Bug 修复描述
   
   ### 优化
   - 优化描述
   ```

3. **重建前端**
   ```bash
   cd multitaskflow/web/frontend
   npm run build
   ```

4. **构建并安装**
   ```bash
   python -m build --wheel
   pip install dist/multitaskflow-x.x.x-py3-none-any.whl --force-reinstall
   ```

## ⚠️ 注意事项

- `package-lock.json` 中的版本号是 npm 依赖的版本，**不需要手动更新**
- `README.md` 中提到的版本号是功能引入版本，**按需更新**
