#!/bin/bash

# HWatch 仓库同步脚本
# 本脚本用于设置双仓库同步并将 feature/english 设为默认分支
# 作者: HWatch Team
# 版本: 0.1.1
# 功能: 配置Git双远程仓库推送，支持同时推送到多个代码托管平台

echo "🚀 开始 HWatch 仓库同步设置..."

# ============================================================================
# 第一步：创建并切换到 feature/english 分支
# ============================================================================
# 检查 feature/english 分支是否存在，如果存在则切换，如果不存在则创建
echo "📋 设置 feature/english 分支..."
if git show-ref --verify --quiet refs/heads/feature/english; then
    # 分支已存在，直接切换
    echo "📋 分支 feature/english 已存在，正在切换到该分支..."
    git switch feature/english
else
    # 分支不存在，创建新分支
    echo "📋 创建新分支 feature/english..."
    git checkout -b feature/english
fi

# ============================================================================
# 第二步：查看当前远程仓库配置
# ============================================================================
# 显示当前所有已配置的远程仓库信息，包括名称和URL
echo "📋 当前 Git 远程仓库配置:"
git remote -v

# ============================================================================
# 第三步：配置远程仓库 URL
# ============================================================================
# 定义两个远程仓库的 URL 地址
# FIRST_REPO_URL: 主要仓库（自建 Gitea 服务器）
# SECOND_REPO_URL: 备份仓库（GitHub 公共仓库）
# 注意：根据实际情况修改这些 URL
FIRST_REPO_URL="https://github.com/GmoneyLtd/hwatch.git"
SECOND_REPO_URL="https://gitea.apuer.tech/GmoneyLtd/hwatch.git"

echo "📋 配置的仓库地址:"
echo "   主仓库: $FIRST_REPO_URL"
echo "   备份仓库: $SECOND_REPO_URL"

# ============================================================================
# 第四步：添加备份远程仓库
# ============================================================================
# 检查是否已存在名为 "backup" 的远程仓库
# 如果不存在则添加，如果已存在则跳过
# if ! git remote | grep -q "^backup$"; then
#     echo "📋 添加备份远程仓库..."
#     git remote add backup "$SECOND_REPO_URL"
#     echo "✅ 已成功添加备份远程仓库: backup -> $SECOND_REPO_URL"
# else
#     echo "📋 备份远程仓库已存在，跳过添加步骤"
# fi

# ============================================================================
# 第五步：设置双仓库推送配置
# ============================================================================
echo "📋 配置双仓库推送设置..."

# 方法1：确保 origin 远程仓库存在并配置正确的 URL
# 获取当前 origin 远程仓库的 URL，如果不存在则返回空
# ORIGIN_URL=$(git remote get-url origin 2>/dev/null)
# if [ -n "$ORIGIN_URL" ]; then
#     # origin 远程仓库已存在
#     echo "📋 当前 origin 远程仓库 URL: $ORIGIN_URL"
# else
#     # origin 远程仓库不存在，需要添加
#     echo "📋 设置 origin 远程仓库..."
#     git remote add origin "$FIRST_REPO_URL"
#     echo "✅ 已添加 origin 远程仓库: origin -> $FIRST_REPO_URL"
# fi

# 方法2：创建一个特殊的 'all' 远程仓库，用于同时推送到多个仓库
# 这是实现双仓库同步的核心配置
if ! git remote | grep -q "^all$"; then
    echo "📋 创建 'all' 远程仓库用于双重推送..."
    
    # 第一步：添加 'all' 远程仓库（设置 fetch 和初始 push URL）
    # Fetch URL: FIRST_REPO_URL
    # Push URL: FIRST_REPO_URL
    git remote add all "$FIRST_REPO_URL"
    
    # 第二步：启用多推送模式并确保第一个仓库在推送列表中
    # 注意：这一步会覆盖默认的Push URL
    # Fetch URL: FIRST_REPO_URL
    # Push URL: FIRST_REPO_URL
    git remote set-url --add --push all "$FIRST_REPO_URL"
    
    # 第三步：为 'all' 远程仓库添加第二个Push URL
    # 现在 'all' 远程仓库将同时推送到两个 URL
    # Fetch URL: FIRST_REPO_URL
    # Push URL: FIRST_REPO_URL SECOND_REPO_URL
    git remote set-url --add --push all "$SECOND_REPO_URL"
    
    echo "✅ 已成功配置 'all' 远程仓库，支持同时推送到两个仓库"
else
    echo "📋 'all' 远程仓库已存在，跳过配置步骤"
fi

# ============================================================================
# 第六步：暂存并提交当前更改
# ============================================================================
echo "📋 暂存并提交当前更改..."

# 将所有更改添加到暂存区
git add .

# 检查是否有需要提交的更改
# git diff --staged --quiet 命令在有暂存更改时返回非零退出码
if git diff --staged --quiet; then
    # 没有更改需要提交
    echo "📋 没有更改需要提交"
else
    # 有更改需要提交，执行提交操作
    echo "📋 正在提交更改..."
    git commit -m "feat: setup dual repository sync and feature/english branch

- Configure repository for dual remote synchronization
- Set feature/english as default development branch
- Add sync script for automated deployment"
    echo "✅ 已成功提交更改"
fi

# ============================================================================
# 第七步：推送到各个远程仓库（包含错误处理）
# ============================================================================
echo "📋 开始推送到远程仓库..."

# 推送到 origin 远程仓库
# 使用 grep -q 检查 origin 远程仓库是否存在
# if git remote | grep -q "^origin$"; then
#     echo "📋 推送到 origin 远程仓库..."
#     # 尝试推送，将错误输出重定向到 /dev/null 以避免显示敏感信息
#     if git push origin feature/english 2>/dev/null; then
#         echo "✅ 成功推送到 origin 远程仓库"
#     else
#         echo "⚠️  推送到 origin 失败（首次设置时这是正常的）"
#         echo "   可能的原因：认证失败、网络问题或远程仓库不存在"
#     fi
# else
#     echo "⚠️  origin 远程仓库不存在，跳过推送"
# fi

# 推送到 backup 远程仓库
# if git remote | grep -q "^backup$"; then
#     echo "📋 推送到 backup 远程仓库..."
#     if git push backup feature/english 2>/dev/null; then
#         echo "✅ 成功推送到 backup 远程仓库"
#     else
#         echo "⚠️  推送到 backup 失败（首次设置时这是正常的）"
#         echo "   可能的原因：认证失败、网络问题或远程仓库不存在"
#     fi
# else
#     echo "⚠️  backup 远程仓库不存在，跳过推送"
# fi

# 推送到 all 远程仓库（双重推送）
# 这是最重要的推送操作，将同时推送到两个仓库
if git remote | grep -q "^all$"; then
    echo "📋 同时推送到所有远程仓库..."
    
    # 获取 'all' 远程仓库的所有推送 URL
    PUSH_URLS=$(git remote get-url --push --all all 2>/dev/null)
    
    if [ -n "$PUSH_URLS" ]; then
        echo "📋 将推送到以下仓库:"
        echo "$PUSH_URLS" | while read -r url; do
            echo "   - $url"
        done
        echo ""
        
        # 执行推送并捕获输出
        PUSH_OUTPUT=$(git push all feature/english 2>&1)
        PUSH_RESULT=$?
        
        if [ $PUSH_RESULT -eq 0 ]; then
            echo "✅ 成功同时推送到所有远程仓库"
            echo "   数据已同步到主仓库和备份仓库"
            
            # 分析输出以显示各个仓库的推送结果
            if echo "$PUSH_OUTPUT" | grep -q "$FIRST_REPO_URL"; then
                echo "   ✅ 主仓库推送成功: $FIRST_REPO_URL"
            fi
            if echo "$PUSH_OUTPUT" | grep -q "$SECOND_REPO_URL"; then
                echo "   ✅ 备份仓库推送成功: $SECOND_REPO_URL"
            fi
        else
            echo "⚠️  部分或全部推送失败"
            
            # 分析错误输出以确定具体哪个仓库失败
            if echo "$PUSH_OUTPUT" | grep -qi "error.*$FIRST_REPO_URL\|fatal.*$FIRST_REPO_URL"; then
                echo "   ❌ 主仓库推送失败: $FIRST_REPO_URL"
            else
                echo "   ✅ 主仓库推送成功: $FIRST_REPO_URL"
            fi
            
            if echo "$PUSH_OUTPUT" | grep -qi "error.*$SECOND_REPO_URL\|fatal.*$SECOND_REPO_URL"; then
                echo "   ❌ 备份仓库推送失败: $SECOND_REPO_URL"
            else
                echo "   ✅ 备份仓库推送成功: $SECOND_REPO_URL"
            fi
            
            echo ""
            echo "   可能的原因:"
            echo "   - 认证失败(检查用户名密码或SSH密钥)"
            echo "   - 网络连接问题"
            echo "   - 远程仓库不存在或没有推送权限"
            echo "   - 分支保护规则阻止推送"
            echo ""
            echo "   详细错误信息:"
            echo "$PUSH_OUTPUT" | sed 's/^/   /'
        fi
    else
        echo "⚠️  无法获取 'all' 远程仓库的推送 URL"
    fi
else
    echo "⚠️  'all' 远程仓库不存在，无法执行双重推送"
fi

# ============================================================================
# 第八步：设置本地默认分支
# ============================================================================
# 将本地仓库的默认分支设置为 feature/english
# 这意味着在克隆或初始化时将默认使用这个分支
echo "📋 设置 feature/english 为本地默认分支..."
git symbolic-ref HEAD refs/heads/feature/english
echo "✅ 已将 feature/english 设置为本地默认分支"

# ============================================================================
# 脚本执行完成，显示配置摘要和后续步骤
# ============================================================================
echo ""
echo "✅ 仓库同步设置完成！"
echo ""
echo "📋 配置摘要:"
echo "   - 默认分支: feature/english"
echo "   - 当前分支: $(git branch --show-current)"
echo "   - 可用的远程仓库:"
git remote -v
echo ""
echo "🔧 后续步骤:"
echo "1. 在远程仓库平台上设置 feature/english 为默认分支:"
echo "   - GitHub: 仓库设置 → 常规 → 默认分支"
echo "   - GitLab/Gitea: 仓库设置 → 仓库 → 默认分支"
echo "2. 更新任何 CI/CD 配置以使用 feature/english 分支"
echo "3. 通知团队成员关于分支变更"
echo ""
echo "💡 已配置的仓库:"
echo "   - 主仓库: $FIRST_REPO_URL"
echo "   - 备份仓库: $SECOND_REPO_URL"
echo ""
echo "💡 日常使用提示:"
echo "   - 同时推送到两个仓库: git push all feature/english"
echo "   - 只推送到主仓库: git push origin feature/english"
echo "   - 只推送到备份仓库: git push backup feature/english"
echo ""
echo "📚 更多信息:"
echo "   - 查看远程仓库配置: git remote -v"
echo "   - 查看分支状态: git branch -a"
echo "   - 查看推送配置: git remote show all"