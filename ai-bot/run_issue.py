import subprocess
import sys
import os
import shutil
import json

# Ensure gh is in PATH
gh_exe_path = shutil.which("gh")
if not gh_exe_path:
    # Common installation paths for GitHub CLI on Windows
    gh_paths = [
        r"C:\Program Files\GitHub CLI",
        os.path.expanduser(r"~\AppData\Local\Programs\GitHub CLI")
    ]
    for path in gh_paths:
        if os.path.exists(path):
            os.environ["PATH"] += os.pathsep + path
            print(f"✅ 已临时添加 GitHub CLI 到 PATH: {path}")
            gh_exe_path = os.path.join(path, "gh.exe")
            break

if not gh_exe_path:
    print("❌ 未找到 GitHub CLI (gh.exe)。请先安装 GitHub CLI: https://cli.github.com/")
    sys.exit(1)

def sh(cmd):
    """Executes a shell command. Uses PowerShell on Windows."""
    # print(f"Executing: {cmd[:50]}..." if len(cmd) > 50 else f"Executing: {cmd}")
    if os.name == 'nt':
        # Use PowerShell on Windows
        # $ErrorActionPreference = 'Stop' ensures we catch errors
        # Force UTF-8 encoding for input/output
        full_cmd = f"$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding; $ErrorActionPreference = 'Stop'; {cmd}"
        return subprocess.check_output(["powershell", "-Command", full_cmd], encoding='utf-8').strip()
    else:
        return subprocess.check_output(cmd, shell=True, encoding='utf-8').strip()

# Check gh auth status
try:
    # Check if logged in
    subprocess.run("gh auth status", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    print("\n❌ GitHub CLI (gh) 未登录")
    print("⚠️  注意：GitHub CLI 用于管理 Issue 和 PR，需要独立于 Git 的授权。")
    print(f"💡 提示：你可以在终端运行以下命令使用浏览器登录：\n   & '{gh_exe_path}' auth login")
    print("   登录成功后，请重新运行此脚本。")
    print("   或者在此处输入 Token 直接登录。")
    
    token = input("请输入 GitHub Personal Access Token (PAT) (直接回车退出): ").strip()
    if token:
        try:
             # Use token to login
             login_cmd = f'gh auth login --with-token'
             process = subprocess.Popen(login_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             stdout, stderr = process.communicate(input=token)
             
             if process.returncode == 0:
                 print("✅ Token 登录成功！")
             else:
                 print(f"❌ Token 登录失败: {stderr}")
                 sys.exit(1)
        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            sys.exit(1)
    else:
        print("❌ 未登录，退出")
        sys.exit(1)

# Get Issue ID
if len(sys.argv) > 1:
    ISSUE_ID = sys.argv[1]
else:
    print("🔍 正在自动获取分配给当前用户的任务...")
    try:
        # Fetch issues assigned to current user
        # limit 30, json format
        # Using sh() which now forces UTF-8
        issue_list_json = sh('gh issue list --assignee "@me" --state open --limit 30 --json number,title')
        issues = json.loads(issue_list_json)
        
        if issues:
            print(f"✅ 找到 {len(issues)} 个分配给当前用户的任务:")
            for i, issue in enumerate(issues):
                print(f"   {i+1}. #{issue['number']} - {issue['title']}")
            
            # Auto select the first one
            ISSUE_ID = str(issues[0]['number'])
            print(f"\n🚀 自动锁定第一个任务: #{ISSUE_ID} - {issues[0]['title']}")
            print("⚠️  (同一时间只能执行一个任务，忽略其他任务)")
        else:
            print("⚠️  当前用户没有分配的 Open Issue。")
            ISSUE_ID = input("请输入 Issue ID (或按 Enter 退出): ").strip()
            
    except Exception as e:
        print(f"❌ 获取任务失败: {e}")
        ISSUE_ID = input("请输入 Issue ID: ").strip()

if not ISSUE_ID:
    print("❌ 未提供 Issue ID，退出")
    sys.exit(1)

# 1. 读取 Issue (AI Bot 读取 Issue: 描述 / 标签 / 模板)
print("\n📌 1. 读取 Issue...")
try:
    # Fetch JSON directly to handle labels properly
    # Using sh() which uses PowerShell on Windows
    issue_json = sh(f'gh issue view {ISSUE_ID} --json title,body,labels')
    data = json.loads(issue_json)
    
    title = data.get('title', '')
    body = data.get('body', '')
    labels = [l['name'] for l in data.get('labels', [])]
    
    # Format for display and prompt
    issue_content = f"Title: {title}\n\nBody:\n{body}\n\nLabels: {', '.join(labels)}"
    print("Issue 内容：")
    print(issue_content)
except Exception as e:
    print(f"❌ 读取 Issue 失败: {e}")
    sys.exit(1)

# 2. Claude Code 分析需求 & 生成实施方案 (Moved BEFORE Branching)
print("\n🤖 2. Claude Code 分析需求 & 生成实施方案...")
# Generate plan using claude CLI
sh(f'''
claude @"
你是一个资深 Python 工程师。
请根据以下 GitHub Issue 给出【实施方案】，不要写代码：

{issue_content}
"@ > plan.md
''')
print("✅ 方案已生成：plan.md")

input("确认方案后按 Enter 继续... (按 Ctrl+C 终止)")

# 3. 自动创建 AI 分支
print(f"\n🌿 3. 自动创建 AI 分支...")
branch_name = f"ai/issue-{ISSUE_ID}"
try:
    sh(f"git checkout -b {branch_name}")
    print(f"✅ 已创建并切换到分支: {branch_name}")
except subprocess.CalledProcessError:
    print(f"⚠️ 分支 {branch_name} 可能已存在，尝试切换...")
    try:
        sh(f"git checkout {branch_name}")
        print(f"✅ 已切换到分支: {branch_name}")
    except Exception as e:
        print(f"❌ 切换分支失败: {e}")
        sys.exit(1)

# 4. Claude Code 修改 Python 代码
print("\n💻 4. Claude Code 修改 Python 代码...")
sh(f'''
claude @"
根据 plan.md 的方案实现代码：
要求：
1. 遵循项目现有 Python 结构
2. 必须可测试
3. 不要修改无关代码
"@
''')
print("✅ 代码修改完成")

# 5. 自动跑测试 (pytest)
print("\n🧪 5. 自动跑测试 (pytest)...")
try:
    sh("pytest")
    print("✅ 测试通过")
except subprocess.CalledProcessError:
    print("❌ 测试失败，请检查代码或手动修复")
    choice = input("测试失败。是否继续提交? (y/N): ").strip().lower()
    if choice != 'y':
        sys.exit(1)

# 6. 提交 commit
print("\n📝 6. 提交 commit...")
try:
    sh("git add .")
    sh(f'git commit -m "feat(ai): implement issue #{ISSUE_ID}"')
    # Using -u origin HEAD to push to current branch name on remote
    sh("git push -u origin HEAD")
    print("✅ 代码已提交")
except subprocess.CalledProcessError as e:
    print(f"❌ 提交/推送失败: {e}")
    choice = input("是否继续创建 PR? (y/N): ").strip().lower()
    if choice != 'y':
        sys.exit(1)

# 7. 创建 Pull Request
print("\n🚀 7. 创建 Pull Request...")
try:
    # Use single line command to ensure compatibility
    sh(f'gh pr create --title "AI: implement issue #{ISSUE_ID}" --body "自动实现 GitHub Issue #{ISSUE_ID}，请 Review" --base develop')
    print("✅ PR 已创建")
except subprocess.CalledProcessError:
    print("⚠️ 创建 PR 失败 (可能已存在或未推送到远程)")
