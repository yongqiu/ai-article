# 🤖 AI News to Article Generator (AI 资讯助手)

这是一款自动化工具，专为技术博主、独立开发者及 AI 爱好者打造。它可以每日自动拉取多个海内外高价值信源的 AI 最新资讯，支持智能筛选评估选题，并最终通过大语言模型 (LLM) 一键生成带有个人观点、“开发者视角”的深度技术长文，非常适合发布在微信公众号、掘金、知乎或个人博客上。

## ✨ 主要特性 (Key Features)

### 🌍 1. 多源全自动聚合 (Multi-Source Aggregation)
聚合了海内外 10+ 高质量内容渠道，确保第一时间捕捉 AI 前沿技术动态，告别信息焦虑：
- **前沿社区**: Hacker News, Reddit (r/MachineLearning, r/LocalLLaMA 等), Product Hunt
- **学术与开源**: arXiv论文, Hugging Face Daily (热门模型/论文), GitHub Trending
- **科技媒体**: TechCrunch, The Verge, VentureBeat, Wired, MIT Tech Review, ZDNet 等
- **官方博客**: OpenAI, Anthropic, Google AI, DeepMind, Meta AI, Stability AI 等

### 🎯 2. 智能多维筛选策略 (Smart Filtering & Sorting)
拒绝信息噪音，只看你关心的垂直内容：
- **多垂直领域支持**: 支持一键切换 通用 LLM、机器人技术 (Robotics)、金融/量化、编程/软件工程、计算机视觉 等细分领域。
- **时间与热度双轴**: 提供“最近 24 小时 (最新)”、“最近 3 天 (热门)”、“最近 7 天 (本周精选)”等多种热度召回策略。

### 🧠 3. LLM 驱动的智能编辑室 (LLM-Powered Editor)
深入对接 DeepSeek/OpenAI 等强大的模型 API，包办从选材到成稿的全管线：
- **智能翻译标题**: 自动将海量英文资讯标题翻译为中文，大幅降低浏览门槛。
- **选题大脑 (Topic Generation)**: 针对选中的碎片化新闻，大模型基于内容关联度自动整合、策划出 5-8 个具备“爆款潜质”的文章选题。
- **极客风深度成文**: 内置硬核 Prompt，摒弃枯燥的机翻味。生成的文章包含 TL;DR、原理解析、**代码示例 (Show me the code)** 及个人观点吐槽，打造真实的“开发者第一视角”沉浸式排版。

### 🚀 4. 灵活的双擎工作流 (Dual Operation Modes)
- **自动采集模式 (Auto)**: `拉取资讯 -> 勾选阅读 -> 生成选题 -> 一键成文` 的全自动流水线作业。
- **手动输入模式 (Manual)**: 发现优质外文长文或遇到突发灵感？直接输入自定义标题的 URL 或粘贴本文，程序将自动抓取网页并结合 LLM 快速完成深度加工。

### 🛠️ 5. 轻量化与易部署 (Lightweight & Easy Setup)
- 基于 Python + Streamlit 打造无刷新交互体验，无重量级 Web 框架，开箱即用。
- 原生支持导出和下载标准 Markdown 格式文件。

## 项目截图
<img width="1826" height="1112" alt="image" src="https://github.com/user-attachments/assets/f11c3d49-d903-4559-b678-615373f724e5" />
<img width="1693" height="1129" alt="image" src="https://github.com/user-attachments/assets/36520bd0-4e92-47e0-91a5-c1f7207b6c37" />
<img width="1570" height="903" alt="image" src="https://github.com/user-attachments/assets/906f5b69-5a41-45dd-92fc-f81b0693bd5f" />
<img width="1722" height="1108" alt="image" src="https://github.com/user-attachments/assets/6fbaea2e-f4f7-45fb-9efb-a5e27f3e6c06" />
<img width="1896" height="708" alt="企业微信截图_f1d96126-141b-407c-bcb0-a800a9af4eba" src="https://github.com/user-attachments/assets/3fb5d0ac-1cdc-4f23-a0c7-a73aea5f5a57" />





---

## 🚀 快速开始

### 1. 环境准备

确保你已经安装了 Python 3.10+。

```bash
# 克隆仓库 (请将下面地址替换为实际 Repo 地址)
git clone https://github.com/your-username/ai-article.git
cd ai-article

# 创建虚拟环境 (可选但极度推荐)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

复制配置模板并填写你的 LLM API Key (原生兼容并推荐使用 DeepSeek，也支持 OpenAI 或兼容形式接口)。

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 LLM_API_KEY
```

> **推荐配置变量 (DeepSeek 示例)**:
> - `LLM_BASE_URL` = `https://api.deepseek.com/v1`
> - `LLM_MODEL` = `deepseek-chat`

### 3. 运行应用

```bash
streamlit run app.py
```
此时系统将在浏览器中自动打开控制台 (通常为 `http://localhost:8501`)。

---

## 🛠️ 使用流程指南

### 🤖 自动采集模式流程
1. **条件设置**: 在左侧/顶部设置你关心的 **领域** 与 **时间跨度**。
2. **获取资讯**: 点击“获取资讯”按钮，系统将多线程爬取并翻译标题。
3. **挑选合并**: 勾选几条高度相关的感兴趣资讯（例如同时勾选"某大模型发布"与"相关代码开源"的资讯）。
4. **生成选题**: 点击“生成选题建议”让 LLM 头脑风暴为您拟定标题和行文方向。
5. **撰写文章**: 选择心仪的选题，大模型将自动拉取原文素材进行结构化的创作。最后点击下载 Markdown 即可！

### ✍️ 手动输入模式流程
针对任意你喜欢的网页链接（支持多个）或直接口述大纲，贴入系统，一键即可生成优质科普评测长文，打破既有信息源的局限。

---

## ⚠️ 注意事项与进阶

- **网络连接**: Hacker News、Reddit 等部分国外信源由于网络限制可能访问较慢或超时，建议在全局稳定的网络代理环境下运行本项目。
- **网页反爬机制**: 由于很多网站加入了 Anti-Bot，如果在手动模式中遇到指定 URL 无法成功抓取，可以采用粘贴文本到“补充文本素材”的方式作为平替。
- **Token 消耗评估**: 从“标题翻译”、“大纲生成”到最后“2000字级别文章撰写”，生成一篇闭环内容预计消耗 3k - 6k Token 请留意 API 调用情况。

## 🔧 进阶：自定义你的信息源

如果你希望加入自己喜欢的作者或网站的 RSS，你可以非常简单地扩展它：
编辑 `utils.py` 中的 `fetch_tech_news_rss` 方法，在 `rss_urls` 列表中加入你想要的 RSS 源即可：

```python
rss_urls = [
    ("https://your-favorite-tech-blog.com/feed/", "My Favorite Blog"),
    # ... 其他源
]
```
（并在 `app.py` 中自行调整抓取条数限制 `limit`）。

---

## 🤝 贡献指南 (Contributing)

非常欢迎提 Issue 或 PR 来共同维护这个工具！无论是增加更优质的信息渠道，提炼更好的 Prompt，还是改善 Web 抓取代码（如增加针对微信公众号文章的完美解析），您的每一滴汗水对这个项目都无比珍贵。

## 📄 许可证 (License)

本项目基于 [MIT License](LICENSE) 协议开源。
