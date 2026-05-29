# 示例：Typo / 极小改动（L1）

## 场景
修复 README.md 中的一个 typo："Recieve" → "Receive"

## 预期流程

1. 用户说："跳过 Trellis，直接把 README.md 里的 'Recieve' 改成 'Receive'"
2. AI 确认 inline 模式（L1）
3. AI 直接编辑 README.md
4. AI 报告：修改了 1 个文件，未创建 task

## 预期产物
- 无（不创建 Trellis task）

## 关键行为
- AI 不会建议创建 task
- AI 不会扩大范围（不会顺便修其他 README 问题）
- AI 报告改了什么
