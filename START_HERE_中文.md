# 你现在先做什么

你已经建好了 GitHub 仓库。这个压缩包就是第一版 demo 的源代码。

## 第一步：在电脑上打开项目

1. 下载并解压 `GetGood-demo.zip`。
2. 打开 VS Code。
3. 选择 **File → Open Folder…**，打开解压后的 `getgood-demo` 文件夹。
4. 左边应该能看到 `run.py`、`requirements.txt`、`frontend`、`backend` 等文件。
5. 选择 **Terminal → New Terminal**。

## 第二步：首次启动（Mac）

下面的命令一行一行运行：

```bash
python3 --version
```

需要 Python 3.10 或以上。如果提示找不到 Python，或版本太旧，把这一步的截图发给我，先安装合适的 Python。

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

首次安装依赖需要联网。安装完成后：

```bash
python run.py
```

在浏览器地址栏输入：

**http://127.0.0.1:8000**

看到 GetGood 首页就说明启动成功。不要关闭运行中的终端；停止时按 Control+C。

以后启动只需要进入项目文件夹、激活 `.venv`，再执行 `python run.py`。

## 第三步：先完整点一次

按 `README.md` 的“演示操作（中文）”走一遍三道题。演示答案按钮会填入测试代码，每次 Submit 都会实际判分。

不用填写 API key，也不需要安装 Node.js。

## 第四步：上传到你已创建的空仓库

先停止服务，或开一个新的 VS Code 终端。在 `getgood-demo` 文件夹内执行：

```bash
git init
git add .
git commit -m "Add working GetGood local demo"
git branch -M main
git remote add origin https://github.com/yiqunqiao/Getgood.git
git push -u origin main
```

如果出现身份设置、登录、origin 已存在或 push 被拒绝等提示，把原始提示发给我。不要使用 force push。

这里上传的是代码；GitHub 仓库不会因此变成在线 demo。第一版按方案在本地演示。

## 这版已经有什么

- 英文界面：练习列表、做题、反馈、成长记录。
- 部分退款、领取代金券、合法第二笔退款三道题。
- 真实 pytest 运行和错误变体判分。
- 第一题分级提示；第二、三题无提示。
- 边界声明核对，包括并发未验证。
- 一键填入演示答案、进度重置。
- 静态 PR 工作流示意页。

## 已知范围

第一版用简单 HTML/CSS/JavaScript 前端替代计划中的 Next.js，以减少启动步骤。当前每题一次标记一条风险，尚未加入自由文本后果说明、风险与测试名的逐条关联。完整判分规则与限制见 README。

这是本地、单学员、可信输入的演示系统。它会在电脑上执行测试代码；不要把执行接口公开到网上，也不要运行陌生人提交的代码。无需真实支付接口，所有付款和钱包操作都是测试对象。
