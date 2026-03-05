import streamlit as st
import os
from dotenv import load_dotenv
from utils import NewsFetcher, LLMProcessor

# 加载环境变量
load_dotenv()

st.set_page_config(
    page_title="AI 资讯文章生成器",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI 资讯文章生成器")
st.markdown("自动拉取每日 AI 资讯或手动输入来源，通过 LLM 生成深度文章。")

# --- Mappings for Localization ---
DOMAIN_MAPPING = {
    "通用 LLM": "General LLM",
    "机器人技术": "Robotics",
    "金融/量化": "Finance/Quant",
    "编程/软件工程": "Programming/SE",
    "计算机视觉": "Computer Vision"
}
DOMAIN_OPTIONS = list(DOMAIN_MAPPING.keys())

TIME_SPAN_MAPPING = {
    "最近 24 小时 (最新)": "Last 24 Hours (Fresh)",
    "最近 3 天 (热门)": "Last 3 Days (Trending)",
    "最近 7 天 (本周精选)": "Last 7 Days (Weekly Best)"
}
TIME_SPAN_OPTIONS = list(TIME_SPAN_MAPPING.keys())

# 来源分类 (用于筛选)
SOURCE_CATEGORIES = {
    "社区讨论": ["Hacker News", "Reddit"],
    "科技媒体": ["TechCrunch", "The Verge", "VentureBeat", "Wired", "Ars Technica", "MIT Tech Review", "ZDNet"],
    "学术论文": ["arXiv", "Hugging Face Daily"],
    "官方博客": ["OpenAI Blog", "Google AI Blog", "Anthropic", "DeepMind", "Meta AI", "Hugging Face Blog", "LangChain", "Stability AI"],
    "开发者": ["GitHub Trending", "InfoQ", "Towards Data Science"],
}

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ 配置")
    
    api_key = os.getenv("LLM_API_KEY")
    if not api_key or "your_api_key" in api_key:
        api_key = st.text_input("DeepSeek/OpenAI API 密钥", type="password")
    else:
        st.success("API Key 已从 .env 加载")
    
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    base_url = st.text_input("基础 URL (Base URL)", value=base_url)
    
    model_name = os.getenv("LLM_MODEL", "deepseek-chat")
    model_name = st.text_input("模型名称 (Model Name)", value=model_name)
    
    st.divider()
    st.info("基于 LLM & Streamlit 构建")

if not api_key:
    st.warning("请在侧边栏或 .env 文件中配置您的 API Key 以继续。")
    st.stop()

# Initialize Processor
llm_processor = LLMProcessor(api_key, base_url, model_name)

# --- Session State Management ---
if 'news_data' not in st.session_state:
    st.session_state.news_data = []
if 'selected_news_indices' not in st.session_state:
    st.session_state.selected_news_indices = []
if 'generated_topics' not in st.session_state:
    st.session_state.generated_topics = []
if 'selected_topic' not in st.session_state:
    st.session_state.selected_topic = None
if 'generated_article' not in st.session_state:
    st.session_state.generated_article = ""

# --- Tabs for Modes ---
tab_auto, tab_manual = st.tabs(["🤖 自动采集模式", "✍️ 手动输入模式"])

# ==========================================
# 模式 1: 自动采集 (Auto-Aggregation)
# ==========================================
with tab_auto:
    st.header("📥 步骤 1: 获取资讯列表")
    
    # Filter UI
    with st.expander("🔍 筛选与设置", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            selected_domains_cn = st.multiselect(
                "主题领域",
                options=DOMAIN_OPTIONS,
                default=["通用 LLM"],
                help="选择特定领域以筛选新闻来源。"
            )
            user_domains = [DOMAIN_MAPPING[d] for d in selected_domains_cn]
            
        with col_f2:
            selected_time_cn = st.selectbox(
                "时间跨度与排序",
                options=TIME_SPAN_OPTIONS,
                index=1,  # 默认选择"最近3天"以获取更多内容
                help="选择'最新'获取最新资讯，或'热门/精选'获取社区验证的热点。"
            )
            user_time_span = TIME_SPAN_MAPPING[selected_time_cn]

    # 来源提示
    st.caption("📡 数据来源: Hacker News, Reddit, arXiv, Hugging Face, TechCrunch, The Verge, VentureBeat, Wired, AI 官方博客, GitHub Trending 等")

    col1, col2 = st.columns([1, 4])
    with col1:
        fetch_news = st.button("🚀 获取资讯", type="primary")

    if fetch_news:
        with st.status("正在从多个来源获取资讯...", expanded=True) as status:
            fetcher = NewsFetcher()
            st.session_state.news_data = []
            st.session_state.selected_news_indices = []
            st.session_state.generated_topics = []
            st.session_state.selected_topic = None
            st.session_state.generated_article = ""
            
            progress_bar = st.progress(0)
            
            # 1. Hacker News
            st.write("1️⃣ 正在获取 Hacker News...")
            hn_news = fetcher.fetch_hacker_news_ai(limit=15, domains=user_domains, time_span=user_time_span)
            st.write(f"   -> Hacker News: {len(hn_news)} 条")
            st.session_state.news_data.extend(hn_news)
            progress_bar.progress(15)
            
            # 2. Hugging Face
            st.write("2️⃣ 正在获取 Hugging Face Daily...")
            hf_news = fetcher.fetch_huggingface_daily(domains=user_domains, time_span=user_time_span)
            st.write(f"   -> Hugging Face: {len(hf_news)} 条")
            st.session_state.news_data.extend(hf_news)
            progress_bar.progress(45)
            
            # 3. Tech RSS
            st.write("3️⃣ 正在获取科技媒体 RSS...")
            rss_news = fetcher.fetch_tech_news_rss(limit=50, domains=user_domains, time_span=user_time_span)
            st.write(f"   -> 科技媒体: {len(rss_news)} 条")
            st.session_state.news_data.extend(rss_news)
            progress_bar.progress(60)
            
            # 4. AI Blogs
            st.write("4️⃣ 正在获取 AI 官方博客...")
            blog_news = fetcher.fetch_ai_blogs(limit=10, domains=user_domains, time_span=user_time_span)
            st.write(f"   -> AI 博客: {len(blog_news)} 条")
            st.session_state.news_data.extend(blog_news)
            progress_bar.progress(90)
            
            # 5. GitHub Trending
            st.write("5️⃣ 正在获取 GitHub Trending...")
            github_news = fetcher.fetch_github_trending(limit=8, domains=user_domains, time_span=user_time_span)
            st.write(f"   -> GitHub: {len(github_news)} 条")
            st.session_state.news_data.extend(github_news)
            progress_bar.progress(95)
            
            # 6. 翻译标题
            total_items = len(st.session_state.news_data)
            if total_items > 0:
                st.write(f"6️⃣ 正在翻译 {total_items} 条资讯标题 (LLM)...")
                # 调用翻译
                llm_processor.translate_news_titles(st.session_state.news_data)
            
            progress_bar.progress(100)
            
            if total_items == 0:
                st.error("未找到任何资讯！请检查网络连接或调整筛选条件。")
                status.update(label="获取失败", state="error")
            else:
                st.success(f"✅ 资讯采集完成，共收集 {total_items} 条数据！")
                status.update(label=f"获取完成: {total_items} 条资讯", state="complete", expanded=False)

    # --- Display News List for Selection ---
    if st.session_state.news_data:
        st.divider()
        st.subheader(f"📋 资讯列表 (共 {len(st.session_state.news_data)} 条)")
        st.markdown("**请勾选您感兴趣的资讯，然后点击下方按钮生成选题。**")
        
        # 按来源分组显示
        news_by_source = {}
        for idx, item in enumerate(st.session_state.news_data):
            source = item.get('source', '其他')
            # 简化来源名称用于分组
            source_group = source
            for category, sources in SOURCE_CATEGORIES.items():
                if any(s in source for s in sources):
                    source_group = category
                    break
            
            if source_group not in news_by_source:
                news_by_source[source_group] = []
            news_by_source[source_group].append((idx, item))
        
        # 使用 tabs 分组显示
        source_tabs = st.tabs(list(news_by_source.keys()) + ["🔍 全部资讯"])
        
        selected_indices = []
        
        for tab_idx, (source_group, items) in enumerate(news_by_source.items()):
            with source_tabs[tab_idx]:
                st.caption(f"共 {len(items)} 条")
                for idx, item in items:
                    col_check, col_content = st.columns([0.05, 0.95])
                    with col_check:
                        is_selected = st.checkbox(
                            f"选择资讯 {idx}",
                            key=f"news_{idx}",
                            value=idx in st.session_state.selected_news_indices,
                            label_visibility="collapsed"
                        )
                        if is_selected and idx not in selected_indices:
                            selected_indices.append(idx)
                    
                    with col_content:
                        source_badge = item.get('source', '')
                        title = item.get('title', 'No Title')
                        title_zh = item.get('title_zh', '')
                        url = item.get('url', '#')
                        summary = item.get('summary', '')[:150]
                        
                        if title_zh:
                            st.markdown(f"**[{title_zh}]({url})**")
                            st.text(f"原文: {title}")
                        else:
                            st.markdown(f"**[{title}]({url})**")
                            
                        st.caption(f"📍 {source_badge} | {summary}...")
        
        # 全部资讯 tab
        with source_tabs[-1]:
            st.caption(f"共 {len(st.session_state.news_data)} 条")
            for idx, item in enumerate(st.session_state.news_data):
                col_check, col_content = st.columns([0.05, 0.95])
                with col_check:
                    is_selected = st.checkbox(
                        f"选择资讯 {idx}",
                        key=f"all_news_{idx}",
                        value=idx in selected_indices or idx in st.session_state.selected_news_indices,
                        label_visibility="collapsed"
                    )
                    if is_selected and idx not in selected_indices:
                        selected_indices.append(idx)
                
                with col_content:
                    source_badge = item.get('source', '')
                    title = item.get('title', 'No Title')
                    title_zh = item.get('title_zh', '')
                    url = item.get('url', '#')
                    summary = item.get('summary', '')[:150]
                    
                    if title_zh:
                        st.markdown(f"**[{title_zh}]({url})**")
                        st.text(f"原文: {title}")
                    else:
                        st.markdown(f"**[{title}]({url})**")

                    st.caption(f"📍 {source_badge} | {summary}...")
        
        # 更新选中状态
        st.session_state.selected_news_indices = selected_indices
        
        # 显示已选数量
        st.divider()
        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.info(f"已选择 {len(st.session_state.selected_news_indices)} 条资讯")
        
        with col_btn:
            generate_topics_btn = st.button(
                "🎯 生成选题建议", 
                type="primary",
                disabled=len(st.session_state.selected_news_indices) == 0
            )

    # --- Step 2: Topic Generation from Selected News ---
    if 'generate_topics_btn' in dir() and generate_topics_btn and st.session_state.selected_news_indices:
        selected_news = [st.session_state.news_data[i] for i in st.session_state.selected_news_indices]
        
        with st.status("正在调用 LLM 分析选题...", expanded=True) as status:
            st.write(f"📊 正在分析 {len(selected_news)} 条资讯...")
            
            topics = llm_processor.generate_topics(selected_news)
            st.session_state.generated_topics = topics
            
            # 重新映射 source_indices
            for topic in st.session_state.generated_topics:
                if 'source_indices' in topic:
                    new_indices = []
                    for rel_idx in topic['source_indices']:
                        if isinstance(rel_idx, int) and 1 <= rel_idx <= len(selected_news):
                            abs_idx = st.session_state.selected_news_indices[rel_idx - 1]
                            new_indices.append(abs_idx + 1)
                    topic['source_indices'] = new_indices
            
            if topics:
                st.write(f"✅ 成功生成 {len(topics)} 个选题建议！")
                status.update(label="选题生成完成", state="complete", expanded=False)
            else:
                st.error("选题生成失败，LLM 未返回有效数据。")
                status.update(label="生成失败", state="error")

    # --- Display Generated Topics ---
    if st.session_state.generated_topics:
        st.divider()
        st.header("🎯 步骤 2: 选择写作选题")
        
        valid_topics = [t for t in st.session_state.generated_topics if 'id' in t]
        
        if not valid_topics:
            st.error("选题数据格式错误，请重试。")
        else:
            topic_options = [f"{t['id']}. {t['title']} | {t['description']}" for t in valid_topics]
            
            selected_option = st.radio(
                "选择一个选题进行写作：",
                options=topic_options,
                index=0
            )
            
            if selected_option:
                selected_id_str = selected_option.split('.')[0]
                for t in valid_topics:
                    if str(t['id']) == selected_id_str:
                        st.session_state.selected_topic = t
                        break
                
                if st.session_state.selected_topic:
                    with st.expander("📚 查看该选题的参考素材", expanded=True):
                        indices = st.session_state.selected_topic.get('source_indices', [])
                        valid_indices = [i for i in indices if isinstance(i, int) and 1 <= i <= len(st.session_state.news_data)]
                        
                        for idx in valid_indices:
                            news_item = st.session_state.news_data[idx-1]
                            st.markdown(f"- **{news_item['source']}**: [{news_item['title']}]({news_item['url']})")

    # --- Step 3: Article Generation (Auto Mode) ---
    if st.session_state.selected_topic:
        st.divider()
        st.header("✍️ 步骤 3: 生成文章")
        
        if st.button("✍️ 开始撰写文章 (Auto)", type="primary"):
            with st.status("正在撰写文章...", expanded=True) as status:
                st.write("📥 正在整理参考素材...")
                
                indices = st.session_state.selected_topic.get('source_indices', [])
                related_news = []
                for idx in indices:
                    if isinstance(idx, int) and 1 <= idx <= len(st.session_state.news_data):
                        related_news.append(st.session_state.news_data[idx-1])
                
                # 如果没有 source_indices，使用所有选中的资讯
                if not related_news and st.session_state.selected_news_indices:
                    related_news = [st.session_state.news_data[i] for i in st.session_state.selected_news_indices[:5]]
                
                st.write(f"   -> 已提取 {len(related_news)} 条相关资讯作为上下文")
                st.write("🤖 LLM 正在进行创作 (可能需要 1-2 分钟)...")
                
                article_content = llm_processor.generate_article(st.session_state.selected_topic, related_news)
                st.session_state.generated_article = article_content
                
                if article_content and "Error" not in article_content:
                    st.write("✅ 文章生成完毕！")
                    status.update(label="写作完成", state="complete", expanded=False)
                else:
                    st.error("文章生成出错")
                    status.update(label="写作失败", state="error")

# ==========================================
# 模式 2: 手动输入 (Manual Input)
# ==========================================
with tab_manual:
    st.header("✍️ 手动输入素材")
    
    col_m1, col_m2 = st.columns([1, 1])
    
    with col_m1:
        manual_title = st.text_input("文章选题/标题", placeholder="例如：DeepSeek 发布新一代推理模型")
        manual_desc = st.text_area("选题思路/描述 (可选)", placeholder="简要描述文章的侧重点...")
    
    with col_m2:
        manual_urls = st.text_area("参考链接 (每行一个)", placeholder="https://example.com/news1\nhttps://example.com/news2", height=150)
        manual_context = st.text_area("补充文本素材 (可选)", placeholder="直接粘贴相关文本内容...", height=150)
        
    manual_generate_btn = st.button("🚀 开始生成文章", type="primary")
    
    if manual_generate_btn:
        if not manual_title:
            st.error("❌ 请输入文章标题")
        elif not manual_urls and not manual_context:
            st.error("❌ 请至少提供一个参考链接或补充文本素材")
        else:
            with st.status("正在处理手动输入内容...", expanded=True) as status:
                # 1. 整理 Topic 对象
                manual_topic = {
                    "id": "manual",
                    "title": manual_title,
                    "description": manual_desc if manual_desc else f"基于用户提供的关于 {manual_title} 的素材进行撰写。"
                }
                
                st.session_state.selected_topic = manual_topic
                
                # 2. 抓取 URL 内容
                related_news = []
                fetcher = NewsFetcher()
                
                if manual_urls:
                    url_list = [u.strip() for u in manual_urls.split('\n') if u.strip()]
                    st.write(f"🌐 正在抓取 {len(url_list)} 个链接的内容...")
                    
                    for url in url_list:
                        content = fetcher.fetch_url_content(url)
                        if content:
                            content['source'] = "User Provided URL"
                            related_news.append(content)
                            st.write(f"   -> 已抓取: {content['title']}")
                        else:
                            st.warning(f"   -> 抓取失败: {url}")
                
                # 3. 添加手动文本
                if manual_context:
                    related_news.append({
                        "source": "User Input Text",
                        "title": "用户补充文本",
                        "url": "Manual Input",
                        "summary": manual_context
                    })
                
                if not related_news:
                    st.error("❌ 未能获取任何有效素材，请检查链接或网络。")
                    status.update(label="处理失败", state="error")
                else:
                    st.write(f"📚 共整理 {len(related_news)} 份参考素材")
                    st.write("🤖 LLM 正在进行创作...")
                    
                    # 4. 生成文章
                    article_content = llm_processor.generate_article(manual_topic, related_news)
                    st.session_state.generated_article = article_content
                    
                    if article_content and "Error" not in article_content:
                        st.write("✅ 文章生成完毕！")
                        status.update(label="写作完成", state="complete", expanded=False)
                    else:
                        st.error("文章生成出错")
                        status.update(label="写作失败", state="error")

# ==========================================
# 公共结果展示区
# ==========================================
if st.session_state.generated_article:
    st.divider()
    st.header("📝 生成的文章")
    
    tab1, tab2 = st.tabs(["预览", "Markdown 源码"])
    
    with tab1:
        st.markdown(st.session_state.generated_article)
        
    with tab2:
        st.code(st.session_state.generated_article, language="markdown")
        
    # 下载按钮
    file_name_suffix = "article"
    if st.session_state.selected_topic:
        # 清理文件名非法字符
        safe_title = "".join(c for c in st.session_state.selected_topic.get('title', 'draft') if c.isalnum() or c in (' ','-','_')).strip().replace(' ','_')
        file_name_suffix = safe_title
        
    st.download_button(
        label="📥 下载为 Markdown",
        data=st.session_state.generated_article,
        file_name=f"{file_name_suffix}.md",
        mime="text/markdown"
    )

# --- Footer ---
st.divider()
st.caption("💡 提示：如果资讯数量较少，可以尝试扩大时间范围或减少领域筛选。")